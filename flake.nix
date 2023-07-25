{
  description = "Arrow notebook";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.default = pkgs.mkShell {
        propagatedBuildInputs = [
          pkgs.python311
          pkgs.pipenv
          pkgs.sqlite
          pkgs.sqlitebrowser
          pkgs.sqldiff
          pkgs.glib
          pkgs.glibc
        ];

      # Environment variables
      # fixes libstdc++ issues and libgl.so issues
      LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib/:/run/opengl-driver/lib/:${pkgs.glib.out}/lib/:${pkgs.qt6.full.out}/lib/";

      # fixes xcb issues :
      QT_PLUGIN_PATH="${pkgs.qt6.qtbase}/${pkgs.qt6.qtbase.qtPluginPrefix}";
      };
    });
}
