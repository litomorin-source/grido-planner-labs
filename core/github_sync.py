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

    def upload_text_file(self, path: str, content: str, commit_message: str):
        url = f"{self.api_base}/repos/{self.repo}/contents/{path}"
        get_resp = requests.get(url, headers=self.headers, params={"ref": self.branch}, timeout=20)

        sha = None
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
        elif get_resp.status_code != 404:
            return {"ok": False, "message": f"No pude consultar archivo existente. Status {get_resp.status_code}", "details": get_resp.text[:500]}

        payload = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(url, headers=self.headers, json=payload, timeout=20)
        if put_resp.status_code in (200, 201):
            return {"ok": True, "message": "Archivo subido correctamente", "commit": put_resp.json().get("commit", {}).get("sha")}
        return {"ok": False, "message": f"No pude subir archivo. Status {put_resp.status_code}", "details": put_resp.text[:500]}
