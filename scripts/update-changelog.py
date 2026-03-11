#!/usr/bin/env python3

import click
import itertools
import json
import logging
import re
import os
import requests

from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from github import Github, UnknownObjectException
try:
    from pydriller import RepositoryMining
except ImportError:
    from pydriller import Repository as RepositoryMining
logging.basicConfig(level=logging.INFO)

# extract text between markers in Pull requests
START_PR_MARKER = '<!--start_release_notes-->\r\n'
END_PR_MARKER = '<!--end_release_notes-->'
DEFAULT_PR_TITLE = '### Release notes feature title'

GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'


@dataclass
class IssueData:
    number: int
    title: str
    url: str


@dataclass
class PullRequestData:
    id: int
    title: str
    html_url: str
    body: str               # may be None for PRs with no description
    linked_issues: list = field(default_factory=list)   # list[IssueData]


@dataclass
class RepoData:
    name: str
    url: str
    tag_from: str
    tag_to: str
    pull_requests: list = field(default_factory=list)   # list[PullRequestData]


# ---------------------------------------------------------------------------
# Formatting functions (pure — no GitHub API calls, no class state)
# ---------------------------------------------------------------------------

def create_changelog(repo_data, format_markdown=False):
    """
    Build changelog lines from a RepoData object.
    format_markdown=True produces Markdown; False produces RST.
    """
    changelog_lines = []

    if len(repo_data.pull_requests) > 1:
        if format_markdown:
            changelog_lines.append('## {} Changelog - [{}]({}/compare/{}...{})'.format(
                repo_data.name, repo_data.tag_to, repo_data.url,
                repo_data.tag_from, repo_data.tag_to))
        else:
            changelog_lines.append('`{}`_'.format(repo_data.tag_to))
            changelog_lines.append(' ---------')

    for pr in repo_data.pull_requests:
        changelog_lines.append("* [#{}]({}) - {}".format(pr.id, pr.html_url, pr.title))

    if not format_markdown:
        changelog_lines.append(".. _`{}`:  {}/compare/{}...{}".format(
            repo_data.tag_to, repo_data.url, repo_data.tag_from, repo_data.tag_to))
    changelog_lines.append("")

    return [l + "\n" for l in changelog_lines]


def release_plat_header(tag_platform, tag_oasislmf, tag_ods, tag_oasisui):
    """Build the Docker images / components header for OasisPlatform release notes."""
    t_plat, t_lmf, t_ods, t_ui = tag_platform, tag_oasislmf, tag_ods, tag_oasisui
    return [
        '## Docker Images (Platform)\n',
        f'* [coreoasis/api_server:{t_plat}](https://hub.docker.com/r/coreoasis/api_server/tags?name={t_plat})\n',
        f'* [coreoasis/model_worker:{t_plat}](https://hub.docker.com/r/coreoasis/model_worker/tags?name={t_plat})\n',
        f'* [coreoasis/model_worker:{t_plat}-debian](https://hub.docker.com/r/coreoasis/model_worker/tags?name={t_plat}-debian)\n',
        f'* [coreoasis/piwind_worker:{t_plat}](https://hub.docker.com/r/coreoasis/piwind_worker/tags?name={t_plat})\n',
        '## Docker Images (User Interface)\n',
        f'* [coreoasis/oasisui_app:{t_ui}](https://hub.docker.com/r/coreoasis/oasisui_app/tags?name={t_ui})\n',
        f'* [coreoasis/oasisui_proxy:{t_ui}](https://hub.docker.com/r/coreoasis/oasisui_proxy/tags?name={t_ui})\n',
        '## Components\n',
        f'* [oasislmf {t_lmf}](https://github.com/OasisLMF/OasisLMF/releases/tag/{t_lmf})\n',
        f'* [ods-tools {t_ods}](https://github.com/OasisLMF/ODS_Tools/releases/tag/{t_ods})\n',
        f'* [Oasis UI {t_ui}](https://github.com/OasisLMF/OasisUI/releases/tag/{t_ui})\n',
        '\n',
    ]


def extract_pr_content(repo_data):
    """
    Extract release note text (between markers) from each PR body in repo_data.
    Returns a list of formatted strings; empty list means no content found.
    """
    logger = logging.getLogger()
    release_note_content = []

    for pr in repo_data.pull_requests:
        if pr.body is None:
            continue

        idx_start = pr.body.find(START_PR_MARKER)
        idx_end = pr.body.rfind(END_PR_MARKER)
        if idx_start == -1 or idx_end == -1:
            continue

        release_desc = pr.body[idx_start + len(START_PR_MARKER):idx_end].strip()
        if not release_desc:
            continue
        if DEFAULT_PR_TITLE in release_desc:
            logger.info(f'Ignoring PR-{pr.id}, release notes have not been updated.  {pr.html_url}')
            continue

        if release_desc.startswith('###'):
            pr_link = f" - [(PR #{pr.id})]({pr.html_url})"
            lines = release_desc.split('\r\n')
            release_note_content.append("\r\n".join([lines[0] + pr_link] + lines[1:]))
        else:
            release_note_content.append(release_desc)
        release_note_content.append('\n\n')

    return release_note_content


def create_release_notes(repo_data):
    """Wrap extracted PR content with a repo section header."""
    pr_notes = extract_pr_content(repo_data)
    if not pr_notes:
        return []
    return ['\n\n', '## {} Notes\n\n'.format(repo_data.name)] + pr_notes + ['\n\n']


# ---------------------------------------------------------------------------
# GitHub data-fetching class
# ---------------------------------------------------------------------------

class ReleaseNotesBuilder:
    """
    Fetches commit/PR/issue data from GitHub (and optionally a local git repo)
    and returns structured RepoData objects ready for formatting.

    When a github_token is provided, PR data and linked issues are fetched in a
    single GraphQL request. Without a token, the script falls back to individual
    REST calls + HTML scraping (slower, more fragile).

    ## packages used
    https://gitpython.readthedocs.io/en/stable/tutorial.html  -- base class used in pydriller
    https://github.com/ishepard/pydriller                     -- analyse git repo
    https://github.com/PyGithub/PyGithub                      -- fetch github data/metadata
    https://click.palletsprojects.com/en/7.x/                 -- cli options

    ## install requirements
    pip install PyGithub pydriller click requests beautifulsoup4
    """

    def __init__(self, github_token=None, github_user='OasisLMF'):
        self.github_token = github_token
        self.github_user = github_user
        self.logger = logging.getLogger()
        self.gh_headers = {'Authorization': f'token {github_token}'} if github_token else {}
        self._tags_cache = {}
        self._github_repos = {}

    # -- internal helpers ----------------------------------------------------

    def _get_github_repo(self, repo_name):
        if repo_name not in self._github_repos:
            self._github_repos[repo_name] = Github(login_or_token=self.github_token).get_repo(
                f'{self.github_user}/{repo_name}')
        return self._github_repos[repo_name]

    def _get_tags_list(self, repo_name):
        if repo_name not in self._tags_cache:
            resp = requests.get(
                f'https://api.github.com/repos/{self.github_user}/{repo_name}/tags?per_page=10',
                headers=self.gh_headers)
            resp.raise_for_status()
            self._tags_cache[repo_name] = resp.json()
        return self._tags_cache[repo_name]

    def _get_commit_refs(self, repo_url, local_path, from_tag, to_tag):
        """Scan commits between two tags and return the set of referenced issue/PR numbers."""
        self.logger.info("Fetching commits between tags {}...{}".format(from_tag, to_tag))
        path = local_path or repo_url
        repo = RepositoryMining(path, from_tag=from_tag, to_tag=to_tag, only_no_merge=True)
        commit_titles = [commit.msg.split('\n\n')[0] for commit in repo.traverse_commits()]
        commit_refs = list(itertools.chain.from_iterable(
            re.findall(r'#\d+', title) for title in commit_titles))
        return set(int(cm[1:]) for cm in commit_refs)

    def _fetch_prs_graphql(self, repo_name, commit_refs):
        """
        Fetch all PR data and linked issues in a single GraphQL request.

        Uses the `closingIssuesReferences` field which returns issues linked via
        "closes #N" / "fixes #N" in the PR body — the same data the REST fallback
        scraped from HTML. Refs that point to issues (not PRs) come back as null
        and are silently skipped.

        Requires an auth token; GitHub's GraphQL endpoint is heavily rate-limited
        without one.
        """
        pr_fragments = "\n".join(
            f'pr_{ref}: pullRequest(number: {ref}) {{'
            f'  number title url body'
            f'  closingIssuesReferences(first: 25) {{ nodes {{ number title url }} }}'
            f'}}'
            for ref in sorted(commit_refs)
        )
        query = f'{{ repository(owner: "{self.github_user}", name: "{repo_name}") {{ {pr_fragments} }} }}'

        resp = requests.post(GITHUB_GRAPHQL_URL, headers=self.gh_headers, json={'query': query})
        resp.raise_for_status()
        result = resp.json()

        if 'errors' in result:
            self.logger.warning(f"GraphQL errors: {result['errors']}")

        repo_result = result.get('data', {}).get('repository', {})
        pull_requests = []
        for pr in repo_result.values():
            if pr is None:
                continue    # ref pointed to an issue, not a PR
            linked_issues = [
                IssueData(number=i['number'], title=i['title'], url=i['url'])
                for i in pr['closingIssuesReferences']['nodes']
            ]
            pull_requests.append(PullRequestData(
                id=pr['number'],
                title=pr['title'],
                html_url=pr['url'],
                body=pr['body'],
                linked_issues=linked_issues,
            ))

        self.logger.info("Fetched {} PRs via GraphQL for {}".format(len(pull_requests), repo_name))
        return pull_requests

    def _fetch_prs_rest(self, github, commit_refs, repo_url):
        """
        Fallback PR fetch using REST API + HTML scraping (used when no auth token).
        Makes N REST calls for PRs and N HTML scrape calls for linked issues.
        """
        pull_requests = []
        for ref in commit_refs:
            try:
                pr = github.get_pull(ref)
            except UnknownObjectException:
                continue    # ref pointed to an issue, not a PR

            linked_issue_nums = self._scrape_linked_issues(pr.number, repo_url)
            linked_issues = [
                IssueData(number=issue.number, title=issue.title, url=issue.html_url)
                for issue in (github.get_issue(n) for n in linked_issue_nums)
            ]
            pull_requests.append(PullRequestData(
                id=pr.number,
                title=pr.title,
                html_url=pr.html_url,
                body=pr.body,
                linked_issues=linked_issues,
            ))

        self.logger.info("Fetched {} PRs via REST for {}".format(len(pull_requests), repo_url))
        return pull_requests

    def _scrape_linked_issues(self, pr_number, repo_url):
        """
        Scrape linked issue numbers from the PR page (REST fallback only).
        BeautifulSoup is only required when running without an auth token.
        """
        issue_urls_found = []
        try:
            r = requests.get(f"{repo_url}/pull/{pr_number}")
            soup = BeautifulSoup(r.text, 'html.parser')
            issue_form = soup.find("form", {"aria-label": re.compile('Link issues')})
            issue_urls_found = [re.findall(r'\d+', i["href"]) for i in issue_form.find_all("a")]
        except Exception as e:
            self.logger.warning(f"Error scraping linked issues for PR-{pr_number}: {e}")

        issue_refs = list(itertools.chain.from_iterable(issue_urls_found))
        self.logger.info("PR-{} linked issues: {}".format(pr_number, issue_refs))
        return set(map(int, issue_refs))

    # -- public API ----------------------------------------------------------

    def _check_gh_rate_limit(self):
        resp = requests.get('https://api.github.com/rate_limit', headers=self.gh_headers)
        resp.raise_for_status()
        return resp.json()

    def _get_tag(self, repo_name, idx=0):
        return self._get_tags_list(repo_name)[idx]['name']

    def _tag_exists(self, repo_name, tag):
        resp = requests.get(
            f'https://github.com/{self.github_user}/{repo_name}/releases/tag/{tag}',
            headers=self.gh_headers)
        if resp.ok:
            return True
        elif resp.status_code == 404:
            return False
        else:
            resp.raise_for_status()

    def _find_milestone(self, repo_name, title):
        """Return milestone number for title, or None if not found."""
        resp = requests.get(
            f'https://api.github.com/repos/{self.github_user}/{repo_name}/milestones?per_page=100',
            headers=self.gh_headers)
        resp.raise_for_status()
        for milestone in resp.json():
            if milestone.get('title') == title:
                return milestone.get('number')
        return None

    def load_data(self, repo_name, local_path=None, tag_from=None, tag_to=None):
        """
        Fetch PR and issue data for a repo between two tags and return a RepoData object.
        Uses GraphQL (single request) when an auth token is available, otherwise
        falls back to REST + HTML scraping.
        """
        local_repo_path = None
        if local_path is not None:
            if os.path.isdir(os.path.join(local_path, '.git')):
                local_repo_path = os.path.abspath(local_path)
            else:
                self.logger.warning(f'".git" folder not found in {local_path}, falling back to fresh clone')

        repo_url = f'https://github.com/{self.github_user}/{repo_name}'
        all_refs = self._get_commit_refs(repo_url, local_repo_path, tag_from, tag_to)

        if self.github_token:
            pull_requests = self._fetch_prs_graphql(repo_name, all_refs)
        else:
            self.logger.warning("No GitHub token provided — using REST fallback (slower, HTML scraping)")
            github = self._get_github_repo(repo_name)
            pull_requests = self._fetch_prs_rest(github, all_refs, repo_url)

        self.logger.info("{} - data fetch complete".format(repo_name))
        return RepoData(
            name=repo_name,
            url=repo_url,
            tag_from=tag_from,
            tag_to=tag_to,
            pull_requests=pull_requests,
        )

    def create_milestones(self, repo_data):
        """
        Assign all PRs and linked issues in repo_data to a GitHub milestone for the release.
        Fetches PyGithub objects by ID on demand — only needed here for the .edit() call.
        """
        github = self._get_github_repo(repo_data.name)
        milestone_num = self._find_milestone(repo_data.name, repo_data.tag_to)

        if milestone_num is None:
            milestone = github.create_milestone(repo_data.tag_to)
        else:
            milestone = github.get_milestone(milestone_num)

        for pr_data in repo_data.pull_requests:
            github.get_pull(pr_data.id).as_issue().edit(milestone=milestone)
            self.logger.info(f'PR-{pr_data.id}, added to milestone "{milestone.title}"')
            for issue_data in pr_data.linked_issues:
                github.get_issue(issue_data.number).edit(milestone=milestone)
                self.logger.info(f'Issue #{issue_data.number}, added to milestone "{milestone.title}"')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _make_builder(github_token, repo=None, from_tag=None):
    """Create a ReleaseNotesBuilder and validate from_tag if provided."""
    builder = ReleaseNotesBuilder(github_token=github_token)
    if repo and from_tag and not builder._tag_exists(repo, from_tag):
        raise click.BadParameter(f"from_tag={from_tag}, not found in the {repo} repository")
    return builder


@click.group()
def cli():
    pass


@cli.command()
@click.option('--github-token', default=None, help='Github OAuth token')
def check_rate_limit(github_token):
    logger = logging.getLogger()
    builder = _make_builder(github_token)
    logger.info(json.dumps(builder._check_gh_rate_limit(), indent=4))


@cli.command()
@click.option('--repo', type=click.STRING, required=True, help="Repo name, e.g. 'OasisLMF', 'OasisUI'")
@click.option('--output-path', type=click.Path(exists=False), default='./CHANGELOG.rst', help='Changelog output path')
@click.option('--local-repo-path', type=click.Path(exists=False), default=None, help='Path to local git repository (optional, skips clone)')
@click.option('--from-tag', required=True, help='Git tag to track changes from')
@click.option('--to-tag', required=True, help='Git tag to track changes to')
@click.option('--github-token', default=None, help='Github OAuth token')
@click.option('--apply-milestone', is_flag=True, help='Add issues to Github milestone (requires OAuth token)')
def build_changelog(repo, from_tag, to_tag, github_token, output_path, apply_milestone, local_repo_path):
    logger = logging.getLogger()
    builder = _make_builder(github_token, repo, from_tag)

    repo_data = builder.load_data(repo_name=repo, local_path=local_repo_path, tag_from=from_tag, tag_to=to_tag)
    changelog_data = create_changelog(repo_data)
    changelog_path = os.path.abspath(output_path)
    logger.info("CHANGELOG OUTPUT:\n" + "".join(changelog_data))

    if apply_milestone:
        builder.create_milestones(repo_data)

    mode = 'r+' if os.path.isfile(changelog_path) else 'w+'
    with open(changelog_path, mode) as cl:
        text = cl.readlines()
        cl.seek(0)
        if len(text) > 3:
            cl.writelines(text[:3] + changelog_data + text[3:])
            logger.info(f'Appended changelog to: "{changelog_path}"')
        else:
            header = [f'{repo} Changelog\n', (len(repo) + 9) * '=' + '\n', '\n']
            cl.writelines(header + changelog_data)
            logger.info(f'Written changelog to new file: "{changelog_path}"')


@cli.command()
@click.option('--repo', type=click.STRING, required=True, help="Repo name, e.g. 'OasisLMF', 'OasisUI'")
@click.option('--output-path', type=click.Path(exists=False), default='./RELEASE.md', help='Release notes output path')
@click.option('--local-repo-path', type=click.Path(exists=False), default=None, help='Path to local git repository (optional, skips clone)')
@click.option('--from-tag', required=True, help='Git tag to track changes from')
@click.option('--to-tag', required=True, help='Git tag to track changes to')
@click.option('--github-token', default=None, help='Github OAuth token')
def build_release(repo, from_tag, to_tag, github_token, output_path, local_repo_path):
    logger = logging.getLogger()
    builder = _make_builder(github_token, repo, from_tag)

    repo_data = builder.load_data(repo_name=repo, local_path=local_repo_path, tag_from=from_tag, tag_to=to_tag)
    release_notes = create_changelog(repo_data, format_markdown=True) + create_release_notes(repo_data)
    logger.info("RELEASE NOTES OUTPUT:\n" + "".join(release_notes))

    release_notes_path = os.path.abspath(output_path)
    with open(release_notes_path, 'w+') as rn:
        rn.writelines(release_notes)
        logger.info(f'Written release notes to: "{release_notes_path}"')


@cli.command()
@click.option('--platform-repo-path', type=click.Path(exists=False), default=None)
@click.option('--platform-from-tag', default=None)
@click.option('--platform-to-tag', default=None)
@click.option('--lmf-repo-path', type=click.Path(exists=False), default=None)
@click.option('--lmf-from-tag', default=None)
@click.option('--lmf-to-tag', default=None)
@click.option('--ods-repo-path', type=click.Path(exists=False), default=None)
@click.option('--ods-from-tag', default=None)
@click.option('--ods-to-tag', default=None)
@click.option('--github-token', default=None, help='Github OAuth token')
@click.option('--output-path', type=click.Path(exists=False), default='./RELEASE.md', help='Release notes output path')
def build_release_platform(platform_repo_path, platform_from_tag, platform_to_tag,
                           lmf_repo_path, lmf_from_tag, lmf_to_tag,
                           ods_repo_path, ods_from_tag, ods_to_tag,
                           github_token, output_path):
    """Create the OasisPlatform release notes."""
    logger = logging.getLogger()
    builder = _make_builder(github_token)

    plat_from = platform_from_tag or builder._get_tag('OasisPlatform', idx=1)
    plat_to   = platform_to_tag   or builder._get_tag('OasisPlatform', idx=0)
    lmf_from  = lmf_from_tag      or builder._get_tag('OasisLMF', idx=1)
    lmf_to    = lmf_to_tag        or builder._get_tag('OasisLMF', idx=0)
    ods_from  = ods_from_tag      or builder._get_tag('ODS_Tools', idx=1)
    ods_to    = ods_to_tag        or builder._get_tag('ODS_Tools', idx=0)
    ui_to     = builder._get_tag('OasisUI', idx=0)

    plat_data = builder.load_data('OasisPlatform', local_path=platform_repo_path, tag_from=plat_from, tag_to=plat_to)
    lmf_data  = builder.load_data('OasisLMF',      local_path=lmf_repo_path,      tag_from=lmf_from,  tag_to=lmf_to)
    ods_data  = builder.load_data('ODS_Tools',     local_path=ods_repo_path,      tag_from=ods_from,  tag_to=ods_to)

    title_line = f'Oasis Release v{plat_to} \n'
    release_notes_data = [title_line, (len(title_line) - 1) * '=' + '\n', '\n']
    release_notes_data += release_plat_header(plat_to, lmf_to, ods_to, ui_to)

    release_notes_data += ["# Changelogs \n", "\n"]
    for data in (plat_data, lmf_data, ods_data):
        release_notes_data += create_changelog(data, format_markdown=True)

    release_notes_data += ["# Release Notes"]
    for data in (plat_data, lmf_data, ods_data):
        release_notes_data += create_release_notes(data)

    logger.info("RELEASE NOTES OUTPUT:\n" + "".join(release_notes_data))

    release_notes_path = os.path.abspath(output_path)
    with open(release_notes_path, 'w+') as rn:
        rn.writelines(release_notes_data)
        logger.info(f'Written release notes to: "{release_notes_path}"')


if __name__ == '__main__':
    cli()
