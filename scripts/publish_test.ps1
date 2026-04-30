$payload = @{
  temperature = 26.1
  humidity = 45.8
  ts = [int][double]::Parse((Get-Date -UFormat %s))
} | ConvertTo-Json -Compress

docker run --rm `
  eclipse-mosquitto:2 `
  mosquitto_pub `
  -h host.docker.internal `
  -p 1883 `
  -t iot/devices/demo-device/telemetry `
  -m $payload

Write-Host "Published test message:"
Write-Host $payload
