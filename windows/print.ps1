$root = "C:\Users\umthr\GitHub\canvas_groups"
$lab = Get-ChildItem -Path $root -Directory -Filter "lab??" | Sort-Object Name | Select-Object -Last 1
$sheets = Get-ChildItem -Path $lab.FullName -Filter *.pdf
foreach ($sheet in $sheets) {
	Start-Process -FilePath $sheet.FullName -Verb Print -PassThru
	Start-Sleep -Seconds 5
}