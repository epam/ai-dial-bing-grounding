import nox

nox.options.reuse_existing_virtualenvs = True

SRC = ["aidial_bing_grounding", "tests", "scripts", "noxfile.py"]


def _targets(session: nox.Session) -> list[str]:
    """Use posargs if provided, otherwise default to SRC."""
    return session.posargs or SRC


def _install(session: nox.Session):
    session.run("poetry", "install", external=True)


def _run_formatters(session: nox.Session, *args):
    session.run("autoflake", *args)
    session.run("isort", *args)
    session.run("black", *args)


@nox.session
def lint(session: nox.Session):
    """Runs all linters and format checks"""
    try:
        _install(session)
        session.run("poetry", "check", "--lock", external=True)
        targets = _targets(session)
        session.run("pyright", *targets)
        session.run("flake8", *targets)
        _run_formatters(session, *targets, "--check")
    except Exception:
        session.error(
            "linting has failed. Run 'make format' to fix formatting"
            " and fix other errors manually"
        )


@nox.session
def format(session: nox.Session):
    """Runs all code formatters"""
    _install(session)
    _run_formatters(session, *_targets(session))


# --- Individual tool sessions ---


@nox.session
def black(session: nox.Session):
    """Runs black formatter"""
    _install(session)
    session.run("black", *_targets(session))


@nox.session
def black_check(session: nox.Session):
    """Checks black formatting"""
    _install(session)
    session.run("black", "--check", *_targets(session))


@nox.session
def isort(session: nox.Session):
    """Runs isort import sorter"""
    _install(session)
    session.run("isort", *_targets(session))


@nox.session
def isort_check(session: nox.Session):
    """Checks isort import sorting"""
    _install(session)
    session.run("isort", "--check-only", "--diff", *_targets(session))


@nox.session
def autoflake(session: nox.Session):
    """Runs autoflake unused import remover"""
    _install(session)
    session.run("autoflake", *_targets(session))


@nox.session
def autoflake_check(session: nox.Session):
    """Checks for unused imports"""
    _install(session)
    session.run("autoflake", "--check", *_targets(session))


@nox.session
def flake8(session: nox.Session):
    """Runs flake8 linter"""
    _install(session)
    session.run("flake8", *_targets(session))


@nox.session
def pyright(session: nox.Session):
    """Runs pyright type checker"""
    _install(session)
    session.run("pyright", *_targets(session))


# --- Test sessions ---


@nox.session
def test(session: nox.Session):
    """Runs unit tests and doc tests"""
    _install(session)
    session.run("pytest", "aidial_bing_grounding", "tests/unit_tests/")


@nox.session
def integration_tests(session: nox.Session):
    """Runs integration tests"""
    _install(session)
    session.run("pytest", "tests/integration_tests/")
