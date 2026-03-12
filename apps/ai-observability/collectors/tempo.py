class TempoCollector(BaseCollector):

    def collect(self) -> Dict[str, Any]:
        log = self.config.log or print
        log.info("Collecting Tempo traces …")

        search_url = f"{self.config.TEMPO_URL}/api/search"

        now = datetime.now(timezone.utc)
        start = int((now - timedelta(hours=1)).timestamp())
        end = int(now.timestamp())

        try:
            resp = requests.get(
                search_url,
                params={
                    "start": start,
                    "end": end,
                    "limit": 20,
                    "q": "{}"
                },
                timeout=self.config.HTTP_TIMEOUT_SECONDS
            )

            resp.raise_for_status()
            data = resp.json()
            traces = data.get("traces", [])

        except Exception as exc:
            log.error("Tempo search failed: %s", exc)
            traces = []

        return {"error_traces": traces}