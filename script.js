document.addEventListener('DOMContentLoaded', function() {
    // Fetch or define your JSON data here (for example purposes)
    const jsonData = `PASTE_YOUR_JSON_REPORT_HERE`;


    try {
        const reportData = JSON.parse(jsonData);

        // Set report metadata
        document.getElementById('timeframe').textContent = reportData.timeframe;
        document.getElementById('custom_date').textContent = reportData.custom_range || 'N/A';
        
        const reportContentDiv = document.getElementById('report-content');
        reportContentDiv.innerHTML = generateReportHtml(reportData.analysis);
        
    } catch (error) {
      console.error("Failed to parse JSON", error)
       document.getElementById('report-content').innerHTML = "<p>Failed to load data</p>";
    }



    function generateReportHtml(analysis) {
        let html = '';
        for (const [sectionName, sectionData] of Object.entries(analysis)) {
             html += `<div class="section"><h2>${formatSectionName(sectionName)}</h2>`;
             if (typeof sectionData === 'string' ) {
                  html += `<p>${sectionData}</p></div>`;
                  continue;
              }
            
             if (Object.keys(sectionData).length > 0) {
                  for (const [key, value] of Object.entries(sectionData)){
                      html += `<h3>${formatSubSectionName(key)}</h3>`;
                    if (typeof value == 'object' && value != null && Object.keys(value).length > 0){
                         html += `<div class="table-container">`
                         if (Array.isArray(value)){
                            html += createTableFromArray(value);
                           
                         } else{
                            html += createTableFromObject(value);
                        }
                         html += `</div>`;
                        
                    } else {
                           html += `<pre>${JSON.stringify(value, null, 2)}</pre>`;
                      }
                  }
             }
            html += `</div>`
          }
          return html;
     }

    function formatSectionName(name){
       return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }
   
      function formatSubSectionName(name) {
          return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      }

      function createTableFromObject(data) {
          let html = `<table><thead><tr>`;
          if (Object.keys(data).length == 0){
             return "<p>No data</p>"
          }
          const firstData = data[Object.keys(data)[0]]

          // Create header
           html += `<th>Key</th>`
           if (typeof firstData === 'object' && firstData != null){
               for (const header of Object.keys(firstData)){
                 html += `<th>${header}</th>`
               }
           } else{
               html += `<th>Value</th>`
           }

          html += `</tr></thead><tbody>`
          // Create Rows
           for (const key of Object.keys(data)){
                 html += `<tr>`
                 html += `<td>${key}</td>`
                if (typeof data[key] === 'object' && data[key] != null){
                 for (const value of Object.values(data[key])){
                   html += `<td>${value}</td>`
                   }
                }else{
                  html += `<td>${data[key]}</td>`
                }
                  html += `</tr>`
           }
           html += `</tbody></table>`
            return html
      }
       function createTableFromArray(data) {
           let html = `<table><thead><tr>`;
             if (data.length == 0){
               return "<p>No data</p>"
              }
            const firstData = data[0];
            if (typeof firstData === 'object' && firstData != null){
              for (const header of Object.keys(firstData)){
                  html += `<th>${header}</th>`
                }
            } else{
              html += `<th>Value</th>`
            }

            html += `</tr></thead><tbody>`

              for (const row of data){
                 html += `<tr>`
                 if (typeof row === 'object' && row != null){
                      for (const value of Object.values(row)){
                           html += `<td>${value}</td>`
                      }
                 }else {
                    html += `<td>${row}</td>`
                 }
                   html += `</tr>`
              }

            html += `</tbody></table>`
            return html;
      }
});
