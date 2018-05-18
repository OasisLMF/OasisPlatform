from flask_sqlalchemy import SQLAlchemy
from flask_security import RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


default_credentials_users = db.Table(
    'default_credentials_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('default_credentials_id', db.Integer(), db.ForeignKey('default_credentials.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text(), unique=True, nullable=False)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))


def check_hash(hashed, plaintext):
    return check_password_hash(hashed, plaintext)


class DefaultCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(255), unique=False, nullable=True)
    active = db.Column(db.Boolean())
    user = db.relationship('User', uselist=False, secondary=default_credentials_users, backref=db.backref('default_credentials', uselist=False))

    @classmethod
    def create(cls, username, password):
        hashed_password = generate_password_hash(password)
        user = User(username=username)
        def_cred = DefaultCredentials(
            password=hashed_password,
            active=True,
            user=user
        )
        db.session.add_all([user, def_cred])
        db.session.commit()
        return def_cred

    def check_password(self, plaintext_password):
        return check_hash(self.password, plaintext_password)

    def set_password(self, plaintext_password):
        hashed_password = generate_password_hash(plaintext_password)
        self.password = hashed_password
