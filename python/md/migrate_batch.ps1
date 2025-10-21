$ErrorActionPreference = 'Stop'
Set-Location 'C:\Dev\astro\tptk'

$env:NODE_OPTIONS = '--max-old-space-size=14336'

$scriptPath = $PSCommandPath
$vercelToken = '12u9EwNeXPAiWcfeGkEgGESA'
$vercelProjectId = 'sacred'
$vercelQueueCheckIntervalSeconds = 600

function CommentCompletedTask {
    param(
        [string]$Book,
        [string]$Review
    )

    if (-not $scriptPath) { return }
    if (-not (Test-Path -Path $scriptPath)) { return }

    $content = Get-Content -Path $scriptPath
    $pattern = "^\s*@\{\s*Book='$Book';\s*Review='$Review'\s*\},"

    for ($i = 0; $i -lt $content.Count; $i++) {
        if ($content[$i] -match $pattern) {
            if ($content[$i] -notmatch '^\s*#') {
                $content[$i] = [regex]::Replace($content[$i], '@\{', '# @{', 1)
                Set-Content -Path $scriptPath -Value $content -Encoding UTF8
            }
            break
        }
    }
}

function Get-VercelQueuedDeploymentCount {
    param(
        [string]$Token,
        [string]$ProjectId
    )

    if (-not $Token -or -not $ProjectId) {
        throw 'Vercel token or project ID is not configured.'
    }

    $headers = @{ Authorization = "Bearer $Token" }
    $url = "https://api.vercel.com/v6/deployments?projectId=$ProjectId&limit=100"

    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -Headers $headers -ErrorAction Stop
        if (-not $response -or -not $response.deployments) { return 0 }

        $deployments = @($response.deployments)
        $queued = @($deployments | Where-Object { $_.state -eq 'QUEUED' })
        return $queued.Count
    }
    catch {
        throw "Failed to query Vercel queue: $_"
    }
}

$locale = 'mymr'

$tasks = @(
    # @{ Book='1V'; Review='para' },
    # @{ Book='2V'; Review='paci' },
    # @{ Book='3V'; Review='vi-maha' },
    # @{ Book='4V'; Review='cula' },
    # @{ Book='5V'; Review='pari' },
    # @{ Book='6D'; Review='sila' },
    # @{ Book='7D'; Review='dn-maha' },
    # @{ Book='8D'; Review='pthi' },
    # @{ Book='9M'; Review='mula' },
    # @{ Book='10M'; Review='majj' },
    # @{ Book='11M'; Review='upar' },
    # @{ Book='12S1'; Review='saga' },
    # @{ Book='12S2'; Review='nida' },
    # @{ Book='13S3'; Review='khan' },
    # @{ Book='13S4'; Review='sala' },
    # @{ Book='14S5'; Review='sn-maha' },
    # @{ Book='15A1'; Review='a1' },
    # @{ Book='15A2'; Review='a2' },
    # @{ Book='15A3'; Review='a3' },
    # @{ Book='15A4'; Review='a4' },
    # @{ Book='16A5'; Review='a5' },
    # @{ Book='16A6'; Review='a6' },
    # @{ Book='16A7'; Review='a7' },
    # @{ Book='17A8'; Review='a8' },
    # @{ Book='17A9'; Review='a9' },
    # @{ Book='17A10'; Review='a10' },
    # @{ Book='17A11'; Review='a11' },
    # @{ Book='18Kh'; Review='kh' },
    # @{ Book='18Dh'; Review='dh' },
    # @{ Book='18Ud'; Review='ud' },
    # @{ Book='18It'; Review='it' },
    # @{ Book='18Sn'; Review='sn' },
    # @{ Book='19Vv'; Review='vv' },
    # @{ Book='19Pv'; Review='pv' },
    # @{ Book='19Th1'; Review='th1' },
    # @{ Book='19Th2'; Review='th2' },
    # @{ Book='20Ap1'; Review='ap1' },
    # @{ Book='20Ap2'; Review='ap2' },
    # @{ Book='21Bu'; Review='bu' },
    # @{ Book='21Cp'; Review='cp' },
    # @{ Book='22J'; Review='ja1' },
    # @{ Book='23J'; Review='ja2' },
    # @{ Book='24Mn'; Review='mn' },
    # @{ Book='25Cn'; Review='cn' },
    # @{ Book='26Ps'; Review='ps' },
    # @{ Book='27Ne'; Review='ne' },
    # @{ Book='27Pe'; Review='pe' },
    # @{ Book='28Mi'; Review='mi' },
    # @{ Book='29Dhs'; Review='dhs' },
    # @{ Book='30Vbh'; Review='vbh' },
    # @{ Book='31Dht'; Review='dht' },
    # @{ Book='31Pu'; Review='pu' },
    # @{ Book='32Kv'; Review='kv' },
    # @{ Book='33Y1'; Review='y1' },
    # @{ Book='33Y2'; Review='y2' },
    # @{ Book='33Y3'; Review='y3' },
    # @{ Book='33Y4'; Review='y4' },
    # @{ Book='33Y5'; Review='y5' },
    # @{ Book='34Y6'; Review='y6' },
    # @{ Book='34Y7'; Review='y7' },
    # @{ Book='34Y8'; Review='y8' },
    # @{ Book='35Y9'; Review='y9' },
    # @{ Book='35Y10'; Review='y10' },
    @{ Book='36P1'; Review='p1-1' },
    @{ Book='37P1'; Review='p1-2' },
    @{ Book='38P2'; Review='p2' },
    @{ Book='39P3'; Review='p3' },
    @{ Book='39P4'; Review='p4' },
    @{ Book='39P5'; Review='p5' },
    @{ Book='39P6'; Review='p6' },
    @{ Book='40P7'; Review='p7' },
    @{ Book='40P8'; Review='p8' },
    @{ Book='40P9'; Review='p9' },
    @{ Book='40P10'; Review='p10' },
    @{ Book='40P11'; Review='p11' },
    @{ Book='40P12'; Review='p12' },
    @{ Book='40P13'; Review='p13' },
    @{ Book='40P14'; Review='p14' },
    @{ Book='40P15'; Review='p15' },
    @{ Book='40P16'; Review='p16' },
    @{ Book='40P17'; Review='p17' },
    @{ Book='40P18'; Review='p18' },
    @{ Book='40P19'; Review='p19' },
    @{ Book='40P20'; Review='p20' },
    @{ Book='40P21'; Review='p21' },
    @{ Book='40P22'; Review='p22' },
    @{ Book='40P23'; Review='p23' },
    @{ Book='40P24'; Review='p24' }
)

foreach ($task in $tasks) {
    Write-Host "=== $($task.Book) / $($task.Review) ===" -ForegroundColor Cyan

    python .\python\md\migrate_tipitaka.py --book $($task.Book) $locale
    if ($LASTEXITCODE -ne 0) { throw "migrate_tipitaka failed for $($task.Book)" }

    # python .\python\md\manage_review_status.py --state review --book $($task.Review) --locale $locale --yes
    # if ($LASTEXITCODE -ne 0) { throw "manage_review_status failed for $($task.Book)" }

    # npm run build
    # if ($LASTEXITCODE -ne 0) { throw "npm run build failed for $($task.Book)" }

    git add .
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        git reset
        Write-Host "No changes for $($task.Book); skipped commit/push." -ForegroundColor Yellow
        CommentCompletedTask -Book $task.Book -Review $task.Review
        continue
    }

    git commit -m "Migrate $($task.Book) $locale"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed for $($task.Book)" }

    while ($true) {
        $queuedDeployments = Get-VercelQueuedDeploymentCount -Token $vercelToken -ProjectId $vercelProjectId

        if ($queuedDeployments -eq 0) {
            Write-Host "Vercel queue is clear; pushing changes for $($task.Book)." -ForegroundColor Green
            git push
            if ($LASTEXITCODE -ne 0) { throw "git push failed for $($task.Book)" }
            break
        }

        Write-Host "Vercel queue has $queuedDeployments deployment(s); waiting $vercelQueueCheckIntervalSeconds seconds before rechecking." -ForegroundColor Yellow
        Start-Sleep -Seconds $vercelQueueCheckIntervalSeconds
    }

    CommentCompletedTask -Book $task.Book -Review $task.Review
}
