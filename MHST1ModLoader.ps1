<#
MHST1 Remaster Mod Loader / Injector
Double-click MHST1ModLoader.exe, or right-click this script -> Run with PowerShell.
Runs on Windows PowerShell 5+ with no Python/Java requirement.
#>
param(
  [string]$GameRoot = (Get-Location).Path,
  [string]$ModsDir = (Join-Path (Get-Location).Path 'mods'),
  [switch]$List,
  [switch]$Install,
  [switch]$Uninstall,
  [switch]$DryRun
)
$ErrorActionPreference = 'Stop'

function Write-Log($m) { Write-Host "[MHST1] $m" }
function Align([int64]$n,[int64]$a){ return [int64]([math]::Ceiling($n / $a) * $a) }
function Read-U16($b,$o){ [BitConverter]::ToUInt16($b,$o) }
function Read-U32($b,$o){ [BitConverter]::ToUInt32($b,$o) }
function Put-U16([byte[]]$b,$o,$v){ [BitConverter]::GetBytes([uint16]$v).CopyTo($b,$o) }
function Put-U32([byte[]]$b,$o,$v){ [BitConverter]::GetBytes([uint32]$v).CopyTo($b,$o) }

function Get-Crc32([string]$s){
  $crc=[uint32]0xffffffff
  $bytes=[Text.Encoding]::UTF8.GetBytes($s)
  foreach($byte in $bytes){
    $crc = $crc -bxor [uint32]$byte
    for($i=0;$i -lt 8;$i++){
      if(($crc -band 1) -ne 0){ $crc = ($crc -shr 1) -bxor [uint32]0xedb88320 }
      else { $crc = ($crc -shr 1) }
    }
  }
  return [uint32]($crc -bxor 0xffffffff)
}


function Inflate-Zlib([byte[]]$bytes){
  $ms = New-Object IO.MemoryStream(,$bytes)
  $null = $ms.ReadByte(); $null = $ms.ReadByte() # zlib header
  $ds = New-Object IO.Compression.DeflateStream($ms,[IO.Compression.CompressionMode]::Decompress)
  $out = New-Object IO.MemoryStream
  $ds.CopyTo($out); $ds.Dispose(); return $out.ToArray()
}
function Deflate-Zlib([byte[]]$bytes){
  $out = New-Object IO.MemoryStream
  # zlib header 78 DA = best compression/default window
  $out.WriteByte(0x78); $out.WriteByte(0xDA)
  $ds = New-Object IO.Compression.DeflateStream($out,[IO.Compression.CompressionLevel]::Optimal,$true)
  $ds.Write($bytes,0,$bytes.Length); $ds.Dispose()
  # Adler32 trailer
  $a=1; $b=0
  foreach($x in $bytes){ $a=($a+$x)%65521; $b=($b+$a)%65521 }
  $adler = (($b -band 0xffff) -shl 16) -bor ($a -band 0xffff)
  $out.WriteByte(($adler -shr 24) -band 255); $out.WriteByte(($adler -shr 16) -band 255); $out.WriteByte(($adler -shr 8) -band 255); $out.WriteByte($adler -band 255)
  return $out.ToArray()
}

function Read-Arc($Path){
  $b=[IO.File]::ReadAllBytes($Path)
  if($b[0] -ne 0x41 -or $b[1] -ne 0x52 -or $b[2] -ne 0x43 -or $b[3] -ne 0){ throw "Not ARC v7: $Path" }
  $count=Read-U16 $b 6
  $entries=@()
  for($i=0;$i -lt $count;$i++){
    $o=8+$i*0x90
    $nameBytes=$b[$o..($o+0x7f)]
    $nul=[Array]::IndexOf($nameBytes,[byte]0)
    if($nul -lt 0){$nul=128}
    $name=[Text.Encoding]::UTF8.GetString($nameBytes,0,$nul)
    $hash=Read-U32 $b ($o+0x80); $cs=Read-U32 $b ($o+0x84); $uf=Read-U32 $b ($o+0x88); $do=Read-U32 $b ($o+0x8c)
    $entries += [pscustomobject]@{Index=$i;Name=$name;Hash=$hash;CompressedSize=$cs;UncompressedSize=($uf -band 0x3fffffff);Flags=($uf -band 0xc0000000);Offset=$do;Compressed=(($uf -band 0x40000000) -ne 0)}
  }
  return [pscustomobject]@{Path=$Path;Bytes=$b;Entries=$entries}
}
function Get-ArcEntryBytes($arc,$e){
  $raw = New-Object byte[] $e.CompressedSize
  [Array]::Copy($arc.Bytes,$e.Offset,$raw,0,$e.CompressedSize)
  if($e.Compressed){ return Inflate-Zlib $raw } else { return $raw }
}
function Rebuild-Arc($ArcPath, $ReplaceMap){
  $arc=Read-Arc $ArcPath
  $entries=@(); $payloads=@(); $seen=@{}
  foreach($e in $arc.Entries){
    $key=$e.Name
    $job=$null
    if($ReplaceMap.ContainsKey($key)){ $job=$ReplaceMap[$key] }
    if($job -ne $null){
      if($job -is [string]){ $srcPath=$job } else { $srcPath=$job.source }
      $raw=[IO.File]::ReadAllBytes($srcPath)
    } else { $raw=Get-ArcEntryBytes $arc $e }
    if($e.Compressed){ $payload=Deflate-Zlib $raw; $flags=0x40000000 } else { $payload=$raw; $flags=0 }
    $entries += [pscustomobject]@{Name=$e.Name;Hash=$e.Hash;CompressedSize=$payload.Length;UncompressedSize=$raw.Length;Flags=$flags;Offset=0}
    $payloads += ,$payload
    $seen[$e.Name]=$true
  }
  foreach($name in $ReplaceMap.Keys){
    if($seen.ContainsKey($name)){ continue }
    $job=$ReplaceMap[$name]
    $allowAdd=$false
    if(!($job -is [string]) -and $job.add){ $allowAdd=$true }
    if(!$allowAdd){ throw "ARC entry not found and add was not true: $name in $ArcPath" }
    $srcPath=$job.source
    $raw=[IO.File]::ReadAllBytes($srcPath)
    $compress=$true
    if(!($job -is [string]) -and $job.compress -ne $null){ $compress=[bool]$job.compress }
    if($compress){ $payload=Deflate-Zlib $raw; $flags=0x40000000 } else { $payload=$raw; $flags=0 }
    $hash = Get-Crc32 $name
    if(!($job -is [string]) -and $job.hash_override -ne $null){ $hash=[uint32]$job.hash_override }
    $entries += [pscustomobject]@{Name=$name;Hash=$hash;CompressedSize=$payload.Length;UncompressedSize=$raw.Length;Flags=$flags;Offset=0}
    $payloads += ,$payload
  }
  $headerSize=8+$entries.Count*0x90; $dataStart=Align $headerSize 0x8000
  $ms=New-Object IO.MemoryStream
  $header=New-Object byte[] $dataStart
  $header[0]=0x41;$header[1]=0x52;$header[2]=0x43;$header[3]=0
  Put-U16 $header 4 7; Put-U16 $header 6 $entries.Count
  $cur=$dataStart
  for($i=0;$i -lt $entries.Count;$i++){
    $cur=Align $cur 0x10; $entries[$i].Offset=$cur
    $o=8+$i*0x90
    $nb=[Text.Encoding]::UTF8.GetBytes($entries[$i].Name)
    [Array]::Copy($nb,0,$header,$o,[Math]::Min(127,$nb.Length))
    Put-U32 $header ($o+0x80) $entries[$i].Hash
    Put-U32 $header ($o+0x84) $entries[$i].CompressedSize
    Put-U32 $header ($o+0x88) ($entries[$i].UncompressedSize -bor $entries[$i].Flags)
    Put-U32 $header ($o+0x8c) $entries[$i].Offset
    $cur += $entries[$i].CompressedSize
  }
  $ms.Write($header,0,$header.Length); $written=$dataStart
  for($i=0;$i -lt $payloads.Count;$i++){
    $target=$entries[$i].Offset
    while($written -lt $target){ $ms.WriteByte(0); $written++ }
    $p=$payloads[$i]; $ms.Write($p,0,$p.Length); $written += $p.Length
  }
  [IO.File]::WriteAllBytes($ArcPath,$ms.ToArray())
}

function Backup-Once($path){
  $rel=[IO.Path]::GetRelativePath($GameRoot,$path)
  $bak=Join-Path $GameRoot (Join-Path '_mhst1_backup' $rel)
  if(!(Test-Path $bak)){ New-Item -ItemType Directory -Force -Path (Split-Path $bak) | Out-Null; Copy-Item $path $bak -Force }
}
function Restore-Backup(){
  $bakRoot=Join-Path $GameRoot '_mhst1_backup'
  if(!(Test-Path $bakRoot)){ Write-Log 'No backup folder found.'; return }
  Get-ChildItem $bakRoot -Recurse -File | ForEach-Object {
    $rel=[IO.Path]::GetRelativePath($bakRoot,$_.FullName)
    $dest=Join-Path $GameRoot $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item $_.FullName $dest -Force
  }
  Write-Log 'Restored backed-up files.'
}


function Patch-Scalar([byte[]]$buf,[int]$off,[string]$typ,$value){
  switch($typ){
    'u8' { $buf[$off]=[byte]$value }
    's8' { $buf[$off]=[byte]([sbyte]$value) }
    'u16' { Put-U16 $buf $off ([uint16]$value) }
    's16' { [BitConverter]::GetBytes([int16]$value).CopyTo($buf,$off) }
    'u32' { Put-U32 $buf $off ([uint32]$value) }
    's32' { [BitConverter]::GetBytes([int32]$value).CopyTo($buf,$off) }
    'f32' { [BitConverter]::GetBytes([single]$value).CopyTo($buf,$off) }
    default { throw "Unknown scalar type $typ" }
  }
}
function Apply-RowClonePatch([byte[]]$data,$patch){
  $rowCountOffset = if($patch.row_count_offset -ne $null){[int]$patch.row_count_offset}else{8}
  $rowBase = [int]$patch.row_base
  $rowSize = [int]$patch.row_size
  if($rowBase -le 0 -or $rowSize -le 0){ throw 'table patch requires row_base and row_size' }
  $countType = if($patch.count_type){[string]$patch.count_type}else{'u32'}
  if($countType -eq 'u16'){ $count=Read-U16 $data $rowCountOffset } else { $count=Read-U32 $data $rowCountOffset }
  $out = New-Object byte[] ($data.Length)
  [Array]::Copy($data,$out,$data.Length)
  $ms = New-Object IO.MemoryStream
  $ms.Write($out,0,$out.Length)
  foreach($add in @($patch.clone_rows)){
    $baseIndex = if($add.base_index -ne $null){[int]$add.base_index}else{$count-1}
    $row = New-Object byte[] $rowSize
    [Array]::Copy($data,$rowBase + $baseIndex*$rowSize,$row,0,$rowSize)
    foreach($edit in @($add.set)){
      $typ = if($edit.type){[string]$edit.type}else{'u32'}
      Patch-Scalar $row ([int]$edit.offset) $typ $edit.value
    }
    $ms.Write($row,0,$row.Length)
    $count++
  }
  $final=$ms.ToArray()
  if($countType -eq 'u16'){ Put-U16 $final $rowCountOffset $count } else { Put-U32 $final $rowCountOffset $count }
  return $final
}
function Apply-TablePatchFile($PatchPath, [hashtable]$ArcJobs){
  $patch = Get-Content $PatchPath -Raw | ConvertFrom-Json
  if($patch.target_file){
    $target = Join-Path $GameRoot $patch.target_file
    Write-Log "TABLE $($patch.target_file) <= $PatchPath"
    if(!$DryRun){
      Backup-Once $target
      $data=[IO.File]::ReadAllBytes($target)
      $patched=Apply-RowClonePatch $data $patch
      [IO.File]::WriteAllBytes($target,$patched)
    }
  } elseif($patch.target_arc -and $patch.target_entry){
    $arcPath = Join-Path $GameRoot $patch.target_arc
    $entryName = $patch.target_entry -replace '/','\'
    Write-Log "TABLE ARC $($patch.target_arc) :: $entryName <= $PatchPath"
    if(!$DryRun){
      $arc=Read-Arc $arcPath
      $entry=$arc.Entries | Where-Object { $_.Name -eq $entryName } | Select-Object -First 1
      if(!$entry){ throw "ARC entry not found: $entryName in $arcPath" }
      $data=Get-ArcEntryBytes $arc $entry
      $patched=Apply-RowClonePatch $data $patch
      $tmpDir=Join-Path $env:TEMP 'mhst1_loader_patches'
      New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
      $tmp=Join-Path $tmpDir (($entryName -replace '[\\/:*?"<>|]','_') + '.bin')
      [IO.File]::WriteAllBytes($tmp,$patched)
      if(!$ArcJobs.ContainsKey($arcPath)){ $ArcJobs[$arcPath]=@{} }
      $ArcJobs[$arcPath][$entryName]=$tmp
    }
  } else { throw "Patch $PatchPath needs target_file or target_arc + target_entry" }
}

function Load-Mods(){
  if(!(Test-Path $ModsDir)){ return @() }
  $mods=@()
  Get-ChildItem $ModsDir -Directory | ForEach-Object {
    $mf=Join-Path $_.FullName 'mod.json'
    if(Test-Path $mf){ $j=Get-Content $mf -Raw | ConvertFrom-Json; $mods += [pscustomobject]@{Root=$_.FullName;Manifest=$j} }
  }
  return $mods | Sort-Object { if($_.Manifest.priority){[int]$_.Manifest.priority}else{0} }
}
function Install-Mods(){
  $mods=Load-Mods
  Write-Log "Found $($mods.Count) mod(s)."
  $arcJobs=@{}
  foreach($m in $mods){
    Write-Log "Planning $($m.Manifest.name)"
    foreach($f in @($m.Manifest.files)){
      $src=Join-Path $m.Root $f.source
      if($f.game_path){
        $rel=$f.game_path -replace '^native:/',''
        $dest=Join-Path $GameRoot $rel
        Write-Log "FILE $rel <= $src"
        if(!$DryRun){ if(Test-Path $dest){Backup-Once $dest}; New-Item -ItemType Directory -Force -Path (Split-Path $dest)|Out-Null; Copy-Item $src $dest -Force }
      } elseif($f.arc -and $f.entry){
        $arcPath=Join-Path $GameRoot $f.arc
        $entry=$f.entry -replace '/','\'
        if(!$arcJobs.ContainsKey($arcPath)){ $arcJobs[$arcPath]=@{} }
        $arcJobs[$arcPath][$entry]=[pscustomobject]@{source=$src; add=$f.add; compress=$f.compress; hash_override=$f.hash_override}
        if($f.add){ Write-Log "ARC ADD $($f.arc) :: $entry <= $src" } else { Write-Log "ARC $($f.arc) :: $entry <= $src" }
      }
    }
    foreach($tp in @($m.Manifest.table_patches)){
      $pp=Join-Path $m.Root $tp
      Apply-TablePatchFile $pp $arcJobs
    }
  }
  foreach($arcPath in $arcJobs.Keys){
    Write-Log "Rebuilding ARC $arcPath"
    if(!$DryRun){ Backup-Once $arcPath; Rebuild-Arc $arcPath $arcJobs[$arcPath] }
  }
  Write-Log 'Install complete.'
}

if(!$List -and !$Install -and !$Uninstall){
  Write-Host 'MHST1 Remaster Mod Loader v1.1.0'
  Write-Host '1) Install mods'
  Write-Host '2) List mods'
  Write-Host '3) Restore backups / uninstall mods'
  $c=Read-Host 'Choose'
  if($c -eq '1'){$Install=$true}elseif($c -eq '2'){$List=$true}elseif($c -eq '3'){$Uninstall=$true}else{exit}
}
if($List){ Load-Mods | ForEach-Object { Write-Host "$($_.Manifest.id) - $($_.Manifest.name) v$($_.Manifest.version)" } }
if($Uninstall){ Restore-Backup }
if($Install){ Install-Mods }
