import nox

nox.options.reuse_existing_virtualenvs = True

SRC = "."


def format_with_args(session: nox.Session, *args):
    session.run("autoflake", *args)
    session.run("isort", *args)
    session.run("black", *args)


MIN_PYTHON_VERSION = "3.11"


@nox.session(python=[MIN_PYTHON_VERSION])
def lint(session: nox.Session):
    """Runs linters and fixers"""
    try:
        session.run("poetry", "install", external=True)
        session.run("poetry", "check", "--lock", external=True)
        session.run("pyright", SRC)
        session.run("flake8", SRC)
        format_with_args(session, SRC, "--check")
    except Exception:
        session.error(
            "linting has failed. Run 'make format' to fix formatting and fix other errors manually"
        )


@nox.session(python=[MIN_PYTHON_VERSION])
def format(session: nox.Session):
    """Runs linters and fixers"""
    session.run("poetry", "install", external=True)
    format_with_args(session, SRC)


@nox.session(python=[MIN_PYTHON_VERSION])
def test(session: nox.Session):
    """Runs unit tests and doc tests"""
    session.run("pytest", "aidial_bing_grounding", "tests/unit_tests/")


@nox.session(python=[MIN_PYTHON_VERSION])
def integration_tests(session: nox.Session):
    """Runs integration tests"""
    session.run("pytest", "tests/integration_tests/")
