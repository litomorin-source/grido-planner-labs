import base64
import requests

class GitHubSync:
    def __init__(self, token: str, repo: str, branch: str = "main"):
        self.token = token
        self.repo = repo
        self.branch = branch
        self.api_base = "https://api.github.com"

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def check_repo(self):
        response = requests.get(f"{self.api_base}/repos/{self.repo}", headers=self.headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return {"ok": True, "message": "Repositorio accesible", "default_branch": data.get("default_branch")}
        return {"ok": False, "message": f"No pude acceder al repositorio. Status {response.status_code}", "details": response.text[:500]}

    def check_branch(self):
        response = requests.get(f"{self.api_base}/repos/{self.repo}/branches/{self.branch}", headers=self.headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return {"ok": True, "message": f"Rama {self.branch} encontrada", "commit_sha": data.get("commit", {}).get("sha")}
        return {"ok": False, "message": f"No pude acceder a la rama {self.branch}. Status {response.status_code}", "details": response.text[:500]}

    def verify(self):
        repo_check = self.check_repo()
        if not repo_check["ok"]:
            return {"ok": False, "repo": repo_check, "branch": None}
        branch_check = self.check_branch()
        return {"ok": branch_check["ok"], "repo": repo_check, "branch": branch_check}

    def _get_existing_sha(self, path: str):
        url = f"{self.api_base}/repos/{self.repo}/contents/{path}"
        response = requests.get(url, headers=self.headers, params={"ref": self.branch}, timeout=20)

        if response.status_code == 200:
            return {"ok": True, "exists": True, "sha": response.json().get("sha")}
        if response.status_code == 404:
            return {"ok": True, "exists": False, "sha": None}

        return {
            "ok": False,
            "exists": None,
            "sha": None,
            "message": f"No pude consultar archivo existente. Status {response.status_code}",
            "details": response.text[:800],
        }

    def upload_bytes_file(self, path: str, content_bytes: bytes, commit_message: str):
        sha_result = self._get_existing_sha(path)
        if not sha_result["ok"]:
            return sha_result

        url = f"{self.api_base}/repos/{self.repo}/contents/{path}"
        payload = {
            "message": commit_message,
            "content": base64.b64encode(content_bytes).decode("utf-8"),
            "branch": self.branch,
        }

        if sha_result["sha"]:
            payload["sha"] = sha_result["sha"]

        response = requests.put(url, headers=self.headers, json=payload, timeout=30)

        if response.status_code in (200, 201):
            data = response.json()
            commit = data.get("commit", {})
            return {
                "ok": True,
                "message": "Archivo subido correctamente",
                "commit": commit.get("sha"),
                "html_url": commit.get("html_url"),
                "path": path,
            }

        return {
            "ok": False,
            "message": f"No pude subir archivo. Status {response.status_code}",
            "details": response.text[:1000],
        }\n