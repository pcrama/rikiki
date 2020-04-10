with import <nixpkgs> {};

(python37.withPackages (ps:
    [ps.flask]
    ++ (if lib.inNixShell
        then [
                ps.autopep8
                ps.pytest
                ps.pytest-flask
                ps.pytest-mock
             ]
        else []))).env
