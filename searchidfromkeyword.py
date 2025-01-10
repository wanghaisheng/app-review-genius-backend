    def search_id_ingoogle(self):
        search_url = "https://www.google.com/search"
        self._get(search_url, params={"q": f"app store {self.app_name}"})
        pattern = fr"{self._base_landing_url}/[a-z]{{2}}/.+?/id([0-9]+)"
        app_id = re.search(pattern, self._response.text).group(1)
        return app_id
    def search_id_insitemap(self):
    parse sitemap into local csv, upload csv to r2
      
    def search id from r2 mysql

        https://mp.weixin.qq.com/s/2H89vOHXWyF0n8G0N8kiiA
