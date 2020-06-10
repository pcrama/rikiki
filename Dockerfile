FROM nixos/nix

RUN nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
RUN nix-channel --update
WORKDIR /rikiki
COPY *.nix /rikiki
RUN nix-env -f default.nix -i -A buildInputs
RUN nix-shell --command true

ENTRYPOINT ["python", "-m", "flask", "run", "--port", "8080", "--host", "0.0.0.0"]

# docker build -t rikiki:latest .
#
# Start docker container from PowerShell (avoids problems with msys2 trying to translate
# '/path:/other' to 'C:\msys64\path;C:\msys64\other').  The `-it' is important
#
#   - have it print the organizer secret to console
#   - detect Ctrl-C properly for the '--rm' to do its job
# docker run -it --rm -v "$((Get-Location).Path):/rikiki" -p 8080:8080 rikiki
