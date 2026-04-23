# Prevent pytest from collecting fixture files as test modules.
collect_ignore_glob = [
    "wave6a/reset_password_tests/*",
    "wave6a/*.py",
    "wave6b/login_selectors/*",
    "wave6b/sonar/src/*",
    "wave6b/sql/*.sql",
    "wave6b/auto_fix/*.py",
]
