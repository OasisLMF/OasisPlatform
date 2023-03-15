#!/usr/bin/env python3

import click
import json
import logging
import re
import os
import requests

from bs4 import BeautifulSoup
from github import Github, UnknownObjectException
try:
    from pydriller import RepositoryMining
except:
    from pydriller import Repository as RepositoryMining
logging.basicConfig(level=logging.INFO)

# extract text between markers in Pull requesuts
START_PR_MARKER = '<!--start_release_notes-->\r\n'
END_PR_MARKER = '<!--end_release_notes-->'
DEFAULT_PR_TITLE = '### Release notes feature title'


class ReleaseNotesBuilder(object):
    """ NOTES
    ## package documentaion
    https://gitpython.readthedocs.io/en/stable/tutorial.html  -- base class used in pydriller
    https://github.com/ishepard/pydriller                     -- analysze git repo
    https://github.com/PyGithub/PyGithub                      -- fetch github data/metadata
    https://click.palletsprojects.com/en/7.x/                 -- cli options

    ## install requirments
    'pip install github pydriller click'
    """

    def __init__(self, github_token=None, github_user='OasisLMF'):
        """
        :param github_token: Github Oauth Token
        :type  github_token: str

        :param github_user: Github user (for repo url)
        :type  github_user: str
        """
        self.github_token = github_token
        self.github_user = github_user
        self.logger = logging.getLogger()

        if github_token:
            self.gh_headers = {'Authorization': f'token {self.github_token}'}
        else:
            self.gh_headers = {}

    def _get_commit_refs(self, repo_url, local_path, from_tag, to_tag):
        """
        Scan all commits between the two tags [`tag_start` .. `tag_end`]
        Extract any text from the commit message showing a github tag reference `#{number}`
        and return a list of ints

        :param repo_url: GitHub URL, used for finding issues/Pull requests
        :type  repo_url: str

        :param local_path: (Optional) path to scan a local repository and cross reference with GitHub
        :type  local_path: Path

        :param from_tag: Git Start Tag
        :type  from_tag: str

        :param to_tag: Git end tag
        :type  to_tag: str

        :return: Github rife references
        :rtype:  List of ints
        """
        self.logger.info("Fetching commits between tags {}...{} ".format(from_tag, to_tag))

        if local_path:
            repo = RepositoryMining(local_path, from_tag=from_tag, to_tag=to_tag)
        else:
            repo = RepositoryMining(repo_url, from_tag=from_tag, to_tag=to_tag)

        commit_list = [re.findall(r'#\d+', commit.msg) for commit in repo.traverse_commits()]
        commit_list = sum(commit_list, [])
        return set(map(lambda cm: int(cm[1:]), commit_list))

    def _get_github_pull_requests(self, github, commit_refs):
        """
        All pull requests have issues but not all issue have pull requests

        calling Issue(id).as_pull_request() will return the PR details 'if it exisits'
        otherwise will rasie 'UnknownObjectException' 404

        This filters out non-PR references
        """
        pull_requeusts = []
        for ref in commit_refs:
            try:
                pull_requeusts.append(github.get_pull(ref))
            except UnknownObjectException:
                pass

        self.logger.info("Filtered github refereces to Pull Requests: {}".format([pr.number for pr in pull_requeusts]))
        return pull_requeusts

    def _get_linked_issues(self, pr_number, repo_url):
        """
        there is no direct way to find which issues are linked to a PR via the github API (yet)
        for the moment this func scraps github using `BeautifulSoup`
        """

        issue_urls_found = []
        try:
            r = requests.get(f"{repo_url}/pull/{pr_number}")
            soup = BeautifulSoup(r.text, 'html.parser')
            issueForm = soup.find("form", {"aria-label": re.compile('Link issues')})
            issue_urls_found = [re.findall(r'\d+', i["href"]) for i in issueForm.find_all("a")]
        except Exception as e:
            self.logger.warning(f"Error fetching linked issue for PR-{pr_number}, {e}")

        issue_refs = sum(issue_urls_found, [])
        self.logger.info("PR-{} linked issues: {}".format(pr_number, issue_refs))
        return set(map(int, issue_refs))

    def _check_gh_rate_limit(self):
        resp = requests.get(
            'https://api.github.com/rate_limit',
            headers=self.gh_headers)
        resp.raise_for_status()
        return resp.json()

    def _get_tag(self, repo_name, idx=0):
        resp = requests.get(
            f'https://api.github.com/repos/{self.github_user}/{repo_name}/tags',
            headers=self.gh_headers)

        resp.raise_for_status()
        if resp.ok:
            tag_data = json.loads(resp.text)
            return tag_data[idx]['name']

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

    def _get_all_tags(self, repo_name):
        resp = requests.get(
            f'https://api.github.com/repos/{self.github_user}/{repo_name}/tags',
            headers=self.gh_headers)

        resp.raise_for_status()
        if resp.ok:
            tag_data = json.loads(resp.text)
            return [tag.get('name')for tag in tag_data]

    def _find_milestone(self, repo_name, title):
        """ return milestone number if title matches, return '-1' if not found
        """
        resp = requests.get(
            f'https://api.github.com/repos/{self.github_user}/{repo_name}/milestones?per_page=100',
            headers=self.gh_headers)

        resp.raise_for_status()
        if resp.ok:
            for milestone in resp.json():
                if milestone.get('title') == title:
                    return milestone.get('number')
            return -1

    def load_data(self, repo_name, local_path=None, tag_from=None, tag_to=None):
        """
        Create a dict of PyGithub objects based on the references found in commit
        messages

        {
            'name': 'OasisLMF',
            'url': 'https://github.com/OasisLMF/OasisLMF'
            'tag_from': '1.15.0',
            'tag_to': '1.16.0',
            'pull_requests': [
                {
                    'id': 772,
                    'pull_request': PullRequest(title="Fix/771 fix genbash", number=772),
                    'linked_issues': [
                        Issue(title="genbash, fmpy calls --create-financial-structure-files when running GUL only ", number=771)
                    ]
                },
                {
                    'id': 774,
                    'pull_request': PullRequest(title="use il summary map even for gul if present", number=774),
                    'linked_issues': [
                        Issue(title="Insured loss summary terms when running ground up only", number=777)
                    ]
                },
                        ... etc ...
                {
                    'id': 815,
                    'pull_request': PullRequest(title="Fix/dev package requirements", number=815),
                    'linked_issues': []
                }
            ]
        }
        """

        local_repo_path = None
        if local_path is not None:
            if os.path.isdir(os.path.join(local_path, '.git')):
                local_repo_path = os.path.abspath(local_path)
            else:
                logger.warning(f'repo_path: ".git" folder not found in {repo_path}, fallback to fresh clone')

        # Load repository data
        github = Github(login_or_token=self.github_token).get_repo(f'{self.github_user}/{repo_name}')

        # Search commits for PR references
        repo_url = f'https://github.com/{self.github_user}/{repo_name}'
        all_refs = self._get_commit_refs(repo_url, local_repo_path, tag_from, tag_to)
        pull_reqs = self._get_github_pull_requests(github, all_refs)

        pull_requests = list()
        for pr in pull_reqs:
            linked_issues = self._get_linked_issues(pr.number, repo_url)
            pull_requests.append({
                "id": pr.number,
                "pull_request": pr,
                "linked_issues": [github.get_issue(ref) for ref in linked_issues]
            })

        self.logger.info("{} - Github data fetch complete".format(repo_name))
        return {
            "name": repo_name,
            "url": repo_url,
            "tag_from": tag_from,
            "tag_to": tag_to,
            "pull_requests": pull_requests
        }

    def create_milestones(self, github_data):
        """
        Scan all issues and pull requests in a `github_data` dict from `self.load_data(...)`
        and Link them into a github milestone for that release
        """
        # Load repository data (is needed?)
        repo_name = github_data.get('name')
        github = Github(login_or_token=self.github_token).get_repo(f'{self.github_user}/{repo_name}')
        milestone_title = github_data.get('tag_to')
        milestone_num = self._find_milestone(github_data.get('name'), milestone_title)

        # Get or Create milestone
        if milestone_num == -1:
            milestone = github.create_milestone(milestone_title)
        else:
            milestone = github.get_milestone(milestone_num)

        # Assgin pull requesuts/issues to milestone
        for pr in github_data.get('pull_requests'):
            pull_request = pr.get('pull_request')
            pull_request.as_issue().edit(milestone=milestone)
            self.logger.info(f'PR-{pull_request.number}, added to milestone "{milestone.title}"')
            for issue in pr.get('linked_issues'):
                issue.edit(milestone=milestone)
                self.logger.info(f'Issue #{issue.number}, added to milestone "{milestone.title}"')

    def create_changelog(self, github_data, format_markdown=False):
        """
        Extract Changelog data from github info `see self.load_data()`
        `format_markdown`: format as markdown for release notes
        """
        changelog_lines = []
        # Add header if at least one PR is found
        if len(github_data['pull_requests']) > 1:
            if format_markdown:
                changelog_lines.append('## {} Changelog - [{}]({}/compare/{}...{})'.format(
                    github_data['name'],
                    github_data['tag_to'],
                    github_data["url"],
                    github_data['tag_from'],
                    github_data['tag_to']))
            else:
                # Add RST style header
                changelog_lines.append('`{}`_'.format(github_data['tag_to']))
                changelog_lines.append(' ---------')

        # Check that at least one Pull request has been picked up
        for pr in github_data['pull_requests']:
            num_issues_linked = len(pr['linked_issues'])
            if num_issues_linked < 1:
                # Case 0: PR has no linked issues
                changelog_lines.append("* [#{}]({}) - {}".format(
                    pr['id'],
                    pr['pull_request'].html_url,
                    pr['pull_request'].title
                ))
            elif num_issues_linked == 1:
                # Case 1: PR has a single linked issue
                changelog_lines.append("* [#{}]({}) - {}".format(
                    pr['linked_issues'][0].number,
                    pr['pull_request'].html_url,
                    pr['linked_issues'][0].title,
                ))
            else:
                # Case 2: PR has multiple linked issues
                changelog_lines.append("* [{}]({}) - {}".format(
                    ', '.join([f'#{issue.number}' for issue in pr['linked_issues']]),
                    pr['pull_request'].html_url,
                    pr['pull_request'].title
                ))

        if not format_markdown:
            # Add RST github compare link
            changelog_lines.append(".. _`{}`:  {}/compare/{}...{}".format(
                github_data['tag_to'],
                github_data["url"],
                github_data['tag_from'],
                github_data['tag_to'],
            ))
        changelog_lines.append("")

        changelog_lines = list(map(lambda l: l + "\n", changelog_lines))
        return changelog_lines

    def release_plat_header(self, tag_platform=None, tag_oasislmf=None, tag_ods=None, tag_oasisui=None, tag_ktools=None):
        """
        Create the header for the OasisPlatform release notes
        """
        t_plat = tag_platform if tag_platform else self._get_tag('OasisPlatform')
        t_lmf = tag_oasislmf if tag_oasislmf else self._get_tag('OasisLMF')
        t_ods = tag_ods if tag_ods else self._get_tag('ODS_Tools')
        t_ktools = tag_ktools if tag_ktools else self._get_tag('ktools')
        t_ui = tag_oasisui if tag_oasisui else self._get_tag('OasisUI')

        plat_header = []
        plat_header.append('## Docker Images (Platform)\n')
        plat_header.append(f'* [coreoasis/api_server:{t_plat}](https://hub.docker.com/r/coreoasis/api_server/tags?name={t_plat})\n')
        plat_header.append(f'* [coreoasis/model_worker:{t_plat}](https://hub.docker.com/r/coreoasis/model_worker/tags?name={t_plat})\n')
        plat_header.append(f'* [coreoasis/model_worker:{t_plat}-debian](https://hub.docker.com/r/coreoasis/model_worker/tags?name={t_plat}-debian)\n')
        plat_header.append(f'* [coreoasis/piwind_worker:{t_plat}](https://hub.docker.com/r/coreoasis/piwind_worker/tags?name={t_plat})\n')
        plat_header.append('## Docker Images (User Interface)\n')
        plat_header.append(f'* [coreoasis/oasisui_app:{t_ui}](https://hub.docker.com/r/coreoasis/oasisui_app/tags?name={t_ui})\n')
        plat_header.append(f'* [coreoasis/oasisui_proxy:{t_ui}](https://hub.docker.com/r/coreoasis/oasisui_proxy/tags?name={t_ui})\n')
        plat_header.append('## Components\n')
        plat_header.append(f'* [oasislmf {t_lmf}](https://github.com/OasisLMF/OasisLMF/releases/tag/{t_lmf})\n')
        plat_header.append(f'* [ods-tools {t_ods}](https://github.com/OasisLMF/OasisLMF/releases/tag/{t_ods})\n')
        plat_header.append(f'* [ktools {t_ktools}](https://github.com/OasisLMF/ktools/releases/tag/{t_ktools})\n')
        plat_header.append(f'* [Oasis UI {t_ui}](https://github.com/OasisLMF/OasisUI/releases/tag/{t_ui})\n')
        plat_header.append('\n')
        return plat_header

    def extract_pr_content(self, github_data):
        """
        Extract release note text between two markers in the Pull_request's body
        """
        release_note_content = []
        has_content = False

        if github_data:
            for pr in github_data.get('pull_requests'):
                pr_body = pr['pull_request'].body
                if pr_body is None:
                    continue

                idx_start = pr_body.find(START_PR_MARKER)
                idx_end = pr_body.rfind(END_PR_MARKER)
                if (idx_start == -1 or idx_end == -1):
                    # skip PR if release note tags are missing
                    continue

                release_desc = pr_body[idx_start + len(START_PR_MARKER):idx_end].strip()
                if len(release_desc) < 1:
                    # skip PR if tags contain an empty string
                    continue
                if DEFAULT_PR_TITLE in release_desc:
                    # skip PR if default template title in text
                    self.logger.info('Ignoring PR-{}, release notes have not been updated.  {}'.format(
                        pr['pull_request'].number,
                        pr['pull_request'].html_url
                    ))
                    continue

                # Add PR link to title
                if release_desc[:3].startswith('###'):
                    pr_link = " - [(PR #{})]({})".format(
                        pr['pull_request'].number,
                        pr['pull_request'].html_url)
                    title = [release_desc.split('\r\n')[0] + pr_link]
                    body = release_desc.split('\r\n')[1:]
                    release_note_content.append("\r\n".join(title + body))
                    release_note_content.append('\n\n')
                else:
                    release_note_content.append(release_desc)
                    release_note_content.append('\n\n')

                has_content = True
        return has_content, release_note_content

    def create_release_notes(self, github_data):
        """ release notes
        """
        release_notes = []
        has_notes, pr_notes = self.extract_pr_content(github_data)
        if has_notes:
            release_notes = ['\n\n']
            release_notes.append('## {} Notes\n\n'.format(github_data.get('name')))
            release_notes += pr_notes + ['\n\n']

        return release_notes


@click.group()
def cli():
    pass


@cli.command()
@click.option('--github-token', default=None, help='Github OAuth token')
def check_rate_limit(github_token):
    logger = logging.getLogger()
    noteBuilder = ReleaseNotesBuilder(github_token=github_token)
    rate_limit_info = noteBuilder._check_gh_rate_limit()
    logger.info(json.dumps(rate_limit_info, indent=4))


@cli.command()
@click.option('--repo', type=click.Choice(['ktools', 'OasisLMF', 'OasisPlatform', 'OasisUI'], case_sensitive=True), required=True)
@click.option('--output-path', type=click.Path(exists=False), default='./CHANGELOG.rst', help='changelog output path')
@click.option('--local-repo-path', type=click.Path(exists=False), default=None, help=' Path to local git repository, used to skip clone step (optional) ')
@click.option('--from-tag', required=True, help='Github tag to track changes from')
@click.option('--to-tag', required=True, help='Github tag to track changes to')
@click.option('--github-token', default=None, help='Github OAuth token')
@click.option('--apply-milestone', is_flag=True, help='Add issues to Github milestone, (requires Github OAuth token)')
def build_changelog(repo, from_tag, to_tag, github_token, output_path, apply_milestone, local_repo_path):
    # Setup
    logger = logging.getLogger()
    noteBuilder = ReleaseNotesBuilder(github_token=github_token)

    # check tags are valid
    if not noteBuilder._tag_exists(repo, from_tag):
        raise click.BadParameter(f"from_tag={from_tag}, not found in the {repo} Repository")

    # Create changelog
    repo_data = noteBuilder.load_data(repo_name=repo, local_path=local_repo_path, tag_from=from_tag, tag_to=to_tag)
    changelog_data = noteBuilder.create_changelog(repo_data)
    changelog_path = os.path.abspath(output_path)
    logger.info("CHANGELOG OUTPUT: \n" + "".join(changelog_data))

    # Add milestones
    if apply_milestone:
        noteBuilder.create_milestones(repo_data)

    mode = 'r+' if os.path.isfile(changelog_path) else 'w+'
    with open(changelog_path, mode) as cl:
        text = cl.readlines()

        if len(text) > 3:
            # Appending to existing file
            cl.seek(0)
            cl.writelines(text[:3] + changelog_data + text[3:])
            logger.info(f'Appended Changelog data to: "{changelog_path}"')
        else:
            # new file or stub
            cl.seek(0)
            header = [f'{repo} Changelog\n']
            header.append((len(header[0]) - 1) * '=' + '\n')
            header.append('\n')
            cl.writelines(header + changelog_data)
            logger.info(f'Written Changelog to new file: "{changelog_path}"')


@cli.command()
@click.option('--repo', type=click.Choice(['ktools', 'OasisLMF', 'OasisUI'], case_sensitive=True), required=True)
@click.option('--output-path', type=click.Path(exists=False), default='./RELEASE.md', help='Release notes output path')
@click.option('--local-repo-path', type=click.Path(exists=False), default=None, help=' Path to local git repository, used to skip clone step (optional) ')
@click.option('--from-tag', required=True, help='Github tag to track changes from')
@click.option('--to-tag', required=True, help='Github tag to track changes to')
@click.option('--github-token', default=None, help='Github OAuth token')
def build_release(repo, from_tag, to_tag, github_token, output_path, local_repo_path):
    logger = logging.getLogger()
    noteBuilder = ReleaseNotesBuilder(github_token=github_token)

    # check tags are valid
    if not noteBuilder._tag_exists(repo, from_tag):
        raise click.BadParameter(f"from_tag={from_tag}, not found in the {repo} Repository")

    # Create release notes
    repo_data = noteBuilder.load_data(repo_name=repo, local_path=local_repo_path, tag_from=from_tag, tag_to=to_tag)
    release_notes = noteBuilder.create_changelog(repo_data, format_markdown=True)
    release_notes += noteBuilder.create_release_notes(repo_data)
    logger.info("RELEASE NOTES OUTPUT: \n" + "".join(release_notes))

    # Write lines to target file
    release_notes_path = os.path.abspath(output_path)
    with open(release_notes_path, 'w+') as rn:
        rn.writelines(release_notes)
        logger.info(f'Written Release notes to new file: "{release_notes_path}"')


@cli.command()
@click.option('--platform-repo-path', type=click.Path(exists=False), default=None, help=' Path to local git repository, used to skip clone step (optional) ')
@click.option('--platform-from-tag', default=None, help='Github tag to track changes from')
@click.option('--platform-to-tag', default=None, help='Github tag to track changes to')
@click.option('--lmf-repo-path', type=click.Path(exists=False), default=None, help=' Path to local git repository, used to skip clone step (optional) ')
@click.option('--lmf-from-tag', default=None, help='Github tag to track changes from')
@click.option('--lmf-to-tag', default=None, help='Github tag to track changes to')
@click.option('--ods-repo-path', type=click.Path(exists=False), default=None, help=' Path to local git repository, used to skip clone step (optional) ')
@click.option('--ods-from-tag', default=None, help='Github tag to track changes from')
@click.option('--ods-to-tag', default=None, help='Github tag to track changes to')
@click.option('--ktools-repo-path', type=click.Path(exists=False), default=None, help=' Path to local git repository, used to skip clone step (optional) ')
@click.option('--ktools-from-tag', default=None, help='Github tag to track changes from')
@click.option('--ktools-to-tag', default=None, help='Github tag to track changes to')
@click.option('--github-token', default=None, help='Github OAuth token')
@click.option('--output-path', type=click.Path(exists=False), default='./RELEASE.md', help='Release notes output path')
def build_release_platform(platform_repo_path,
                           platform_from_tag,
                           platform_to_tag,

                           lmf_repo_path,
                           lmf_from_tag,
                           lmf_to_tag,

                           ods_repo_path,
                           ods_from_tag,
                           ods_to_tag,

                           ktools_repo_path,
                           ktools_from_tag,
                           ktools_to_tag,

                           github_token,
                           output_path):
    """
    Create the OasisPlatform release notes
    """
    logger = logging.getLogger()
    noteBuilder = ReleaseNotesBuilder(github_token=github_token)

    plat_from = platform_from_tag if platform_from_tag else noteBuilder._get_tag(repo_name='OasisPlatform', idx=1)
    plat_to = platform_to_tag if platform_to_tag else noteBuilder._get_tag(repo_name='OasisPlatform', idx=0)
    lmf_from = lmf_from_tag if lmf_from_tag else noteBuilder._get_tag(repo_name='OasisLMF', idx=1)
    lmf_to = lmf_to_tag if lmf_to_tag else noteBuilder._get_tag(repo_name='OasisLMF', idx=0)
    ods_from = ods_from_tag if ods_from_tag else noteBuilder._get_tag(repo_name='ODS_Tools', idx=1)
    ods_to = ods_to_tag if ods_to_tag else noteBuilder._get_tag(repo_name='ODS_Tools', idx=0)
    ktools_from = ktools_from_tag if ktools_from_tag else noteBuilder._get_tag(repo_name='ktools', idx=1)
    ktools_to = ktools_to_tag if ktools_to_tag else noteBuilder._get_tag(repo_name='ktools', idx=0)

    ui_to = noteBuilder._get_tag(repo_name='OasisUI', idx=0)

    # Load github data
    plat_data = noteBuilder.load_data(repo_name='OasisPlatform', local_path=platform_repo_path, tag_from=plat_from, tag_to=plat_to)
    lmf_data = noteBuilder.load_data(repo_name='OasisLMF', local_path=lmf_repo_path, tag_from=lmf_from, tag_to=lmf_to)
    ods_data = noteBuilder.load_data(repo_name='ODS_Tools', local_path=ods_repo_path, tag_from=ods_from, tag_to=ods_to)
    ktools_data = noteBuilder.load_data(repo_name='ktools', local_path=ktools_repo_path, tag_from=ktools_from, tag_to=ktools_to)

    # Add title
    release_notes_data = [f'Oasis Release v{plat_to} \n']
    release_notes_data.append((len(release_notes_data[0]) - 1) * '=' + '\n')
    release_notes_data.append('\n')

    # Print docker images and components
    release_notes_data += noteBuilder.release_plat_header(
        tag_platform=plat_to,
        tag_oasislmf=lmf_to,
        tag_ods=ods_to,
        tag_ktools=ktools_to,
        tag_oasisui=ui_to)

    # Load Change logs
    release_notes_data += ["# Changelogs \n", "\n"]
    release_notes_data += noteBuilder.create_changelog(plat_data, format_markdown=True)
    release_notes_data += noteBuilder.create_changelog(lmf_data, format_markdown=True)
    release_notes_data += noteBuilder.create_changelog(ods_data, format_markdown=True)
    release_notes_data += noteBuilder.create_changelog(ktools_data, format_markdown=True)

    # Extract Feature notes from PR's
    release_notes_data += ["# Release Notes"]
    release_notes_data += noteBuilder.create_release_notes(plat_data)
    release_notes_data += noteBuilder.create_release_notes(lmf_data)
    release_notes_data += noteBuilder.create_release_notes(ods_data)
    release_notes_data += noteBuilder.create_release_notes(ktools_data)
    logger.info("RELEASE NOTES OUTPUT: \n" + "".join(release_notes_data))

    # Write lines to target file
    release_notes_path = os.path.abspath(output_path)
    with open(release_notes_path, 'w+') as rn:
        rn.writelines(release_notes_data)
        logger.info(f'Written Release notes to new file: "{release_notes_path}"')


if __name__ == '__main__':
    cli()
