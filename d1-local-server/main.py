import json
import re
import urllib.parse

# pyrefly: ignore [missing-import]
from workers import Response, WorkerEntrypoint


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        env = self.env
        url = request.url
        method = request.method
        print(f"url: {url}, method: {method}")

        # パスの抽出
        path = urllib.parse.urlparse(url).path

        # 末尾が /raw または /query である場合にマッチ
        is_query = path.endswith("/raw") or path.endswith("/query")

        if method == "POST" and is_query:
            account_id = "local"
            database_id = "local"
            match = re.search(r"/accounts/([^/]+)/d1/database/([^/]+)", path)
            if match:
                account_id, database_id = match.groups()

            try:
                body = await request.json()
                body_py = body.to_py() if hasattr(body, "to_py") else body

                sql = body_py.get("sql")
                params = body_py.get("params", [])

                # クエリの実行
                statement = env.DB.prepare(sql).bind(*params)
                db_res = await statement.all()

                # D1 Pythonバインディングのメタデータから変更行数を取得
                db_meta = (
                    db_res.meta.to_py()
                    if hasattr(db_res.meta, "to_py")
                    else db_res.meta
                )
                changes = db_meta.get("changes", 0) if db_meta else 0
                duration = db_meta.get("duration", 0) if db_meta else 0
                last_row_id = db_meta.get("last_row_id") if db_meta else None

                # results を raw 形式に変換
                results_raw = db_res.results.to_py() if db_res.results else []
                columns = []
                rows = []
                if results_raw:
                    first = results_raw[0]
                    if isinstance(first, dict):
                        columns = list(first.keys())
                        for row in results_raw:
                            rows.append([row.get(col) for col in columns])
                else:
                    # 結果が空で SELECT クエリの場合、カラム名を取得するために raw() を試みる
                    if sql.strip().upper().startswith("SELECT"):
                        try:
                            stmt2 = env.DB.prepare(sql).bind(*params)
                            raw_res = await stmt2.raw({"columnNames": True})
                            raw_res_py = (
                                raw_res.to_py()
                                if hasattr(raw_res, "to_py")
                                else raw_res
                            )
                            if raw_res_py and len(raw_res_py) > 0:
                                columns = list(raw_res_py[0])
                        except Exception as e:
                            print(f"Failed to get column names: {e}")

                mock_response = {
                    "result": [
                        {
                            "success": True,
                            "meta": {
                                "served_by": "local-worker-d1-api",
                                "account_id": account_id,
                                "database_id": database_id,
                                "changes": changes,
                                "duration": duration,
                                "last_row_id": last_row_id,
                            },
                            "results": {
                                "columns": columns,
                                "rows": rows,
                            },
                        }
                    ],
                    "success": True,
                    "errors": [],
                    "messages": [],
                }
                print(f"Response: {mock_response}")
                return Response(
                    json.dumps(mock_response),
                    headers={"Content-Type": "application/json"},
                )

            except Exception as e:
                error_response = {
                    "result": None,
                    "success": False,
                    "errors": [
                        {"code": 1000, "message": f"D1 Local Mock Error: {str(e)}"}
                    ],
                    "messages": [],
                }
                print(f"Error: {error_response}")
                return Response(
                    json.dumps(error_response),
                    headers={"Content-Type": "application/json"},
                    status=500,
                )

        return Response("Not Found", status=404)
