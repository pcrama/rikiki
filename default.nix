# Source: https://datakurre.pandala.org/2015/10/nix-for-python-developers.html/
with import <nixpkgs> {};
stdenv.mkDerivation rec {
  name = "env";

  # Mandatory boilerplate for buildable env
  env = buildEnv { name = name; paths = buildInputs; };
  builder = builtins.toFile "builder.sh" ''
    source $stdenv/setup; ln -s $env $out
  '';

  # Customizable development requirements
  buildInputs = [
    # Add packages from nix-env -qaP | grep -i <package-name>
    graphviz
    jre
    plantuml

    # With Python configuration requiring a special wrapper
    (python37.buildEnv.override {
      ignoreCollisions = true;
      extraLibs = with python37Packages; [
        # Add pythonPackages without the prefix
        flask
      ] ++ (if lib.inNixShell
            then [
                    autopep8
                    mypy
                    pydocstyle
                    pytest
                    pytest-flask
                    pytest-mock
                 ]
            else []);
    })
  ];

  # Customizable development shell setup
  shellHook = ''
    export PATH="$PWD/scripts:$PATH"
  '';
}
