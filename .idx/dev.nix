{ pkgs }: {
  channel = "stable-24.05";
  packages = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.nodejs_20
    pkgs.docker
    pkgs.redis
  ];
  idx.extensions = [
    "ms-python.python"
    "bradlc.vscode-tailwindcss"
    "esbenp.prettier-vscode"
  ];
  idx.previews = {
    enable = true;
    previews = {
      api = {
        command = ["uvicorn" "api.main:app" "--host" "0.0.0.0" "--port" "8000" "--reload"];
        manager = "web";
        port = 8000;
      };
    };
  };
}
