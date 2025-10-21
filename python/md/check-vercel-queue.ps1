$token = "12u9EwNeXPAiWcfeGkEgGESA"
$projectId = "sacred"
$url = "https://api.vercel.com/v6/deployments?projectId=$projectId&limit=100"

(Invoke-RestMethod -Uri $url -Method Get -Headers @{ Authorization = "Bearer $token" }).deployments | 
Where-Object { $_.state -eq "QUEUED" } | 
Measure-Object | 
Select-Object -ExpandProperty Count