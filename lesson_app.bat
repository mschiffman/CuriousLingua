<# :
@echo off
rem ===================================================================
rem  Lesson app: one window that takes a .md file all the way to a lesson
rem  on the site, for every strand (reading, listening, speaking, vocabulary,
rem  expressions, grammar, pronunciation, fundamentals):
rem    .md  ->  lesson file  ->  pictures  ->  audio  ->  upload  ->  offline copy
rem  Steps that are already done are checked and skipped.
rem  Double-click to open. Close this console window to stop the app.
rem  Everything below is PowerShell; this file runs itself through it.
rem ===================================================================
set "LESSON_APP_BAT=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -STA -Command "iex ([IO.File]::ReadAllText($env:LESSON_APP_BAT, [Text.Encoding]::UTF8))"
if errorlevel 1 pause
exit /b
#>

# ---------------------------------------------------------------------------
#  The three folders this app reads from. Change them here if they move.
$MdDir     = "C:\Users\mschi\OneDrive\Desktop\story-md"   # the .md files
$Downloads = "C:\Users\mschi\Downloads"                   # new pictures: 1.png, 2.png ...
$YouTube   = "G:\My Drive\_YOUTUBE"                       # where the original PNGs are kept
# ---------------------------------------------------------------------------
#  What each step runs (from this folder, the site folder):
#
#  1 Lesson file    python -E tools\from_md.py make <file.md> --name .. --level .. --topic .. --images ..
#                   -> content\<course>\<strand>\<name>.json, then the pages are rebuilt.
#                   SKIPPED when the lesson file is already there ("Remake from .md" replaces its text).
#                   The .md formats of every lesson type are described at the top of tools\from_md.py
#                   (button "The .md formats").
#  2 Pictures       picture stories only. Moves the numbered PNGs (1.png, 2.png ...) from Downloads to
#                   G:\My Drive\_YOUTUBE\<folder>, then
#                   python tools\convert.py "<_YOUTUBE folder>" --scale 0.8 -o "img\ytstory\<folder>"
#                   (80% size, MozJPEG quality 75: the same as 1_images.bat).
#                   SKIPPED when every picture of the story is already in img\. PNGs that were moved
#                   earlier but not converted are only converted.
#  3 Audio          python -E tools\audio.py make <lesson> --only N N ...      (numbered clips)
#                   python -E tools\audio.py words <lesson>                    (word lists)
#                   SKIPPED when no clip is missing. New takes: make --redo N N / words --redo file.mp3
#  4 Upload         python -E tools\audio.py upload <lesson>   (R2, new ?v= tag, CDN check, rebuild)
#                   SKIPPED when the lesson already has its tag and this run made no clips.
#  5 Offline copy   python -E tools\offline.py <lesson>  -> <course>\single\<strand>__<name>.html
#                   SKIPPED when the copy is newer than the lesson file and this run changed nothing.
#
#  "Run the remaining steps" does 1 to 5 in order for the chosen .md, after showing the plan and
#  what it costs. It stops at the first step that fails.
#  Putting pages on the website is still 5_publish.bat (commit and push).
# ---------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path $env:LESSON_APP_BAT          # the site folder
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
if ($env:LESSON_APP_MD) { $MdDir = $env:LESSON_APP_MD }                  # for the self-test
if ($env:LESSON_APP_DOWNLOADS) { $Downloads = $env:LESSON_APP_DOWNLOADS }

# ------------------------------------------------------------------ helpers
function Get-EnvVar($name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not $v) { $v = [Environment]::GetEnvironmentVariable($name, "User") }
    if ($v) { return $v.Trim() }
    return $null
}

function Quote($s) { return '"' + ([string]$s).Replace('"', '') + '"' }

function Invoke-Python($arguments) {
    # runs python and returns what it printed (UTF-8); used for the quick status call
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = $arguments
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [Text.Encoding]::UTF8
    $p = [System.Diagnostics.Process]::Start($psi)
    $errTask = $p.StandardError.ReadToEndAsync()
    $out = $p.StandardOutput.ReadToEnd()
    $p.WaitForExit()
    return [pscustomobject]@{ Code = $p.ExitCode; Out = $out; Err = $errTask.Result }
}

function Get-Stories {
    $r = Invoke-Python ('-E tools\from_md.py status --json --md ' + (Quote $MdDir) + ' --yt ' + (Quote $YouTube))
    if ($r.Code -ne 0 -or -not $r.Out) {
        Write-Line ""
        Write-Line "Could not read the .md folder:"
        Write-Line ($r.Err + $r.Out)
        return @()
    }
    return @((ConvertFrom-Json $r.Out).rows)
}

function Get-NumberedPngs($dir) {
    if (-not (Test-Path -LiteralPath $dir)) { return @() }
    return @(Get-ChildItem -LiteralPath $dir -File | Where-Object { $_.Name -match '^\d+\.png$' } | Sort-Object { [int]$_.BaseName })
}

function Get-PictureState($s) {
    # what the pictures step would do for this story
    $o = [pscustomobject]@{ Applies = $false; Need = @(); Folder = ""; Out = ""; Src = ""; InSrc = @(); InDl = @(); Other = @(); Action = "none"; Text = "" }
    if ($s.kind -ne "reader" -or -not $s.pictures.dir) { $o.Text = "no picture folder for this kind of lesson"; return $o }
    $o.Applies = $true
    $o.Folder = ($s.pictures.dir.TrimEnd('/') -split '/')[-1]
    $o.Out = Join-Path $Root ($s.pictures.dir.TrimEnd('/').Replace('/', '\'))
    $o.Src = Join-Path $YouTube $o.Folder
    $o.Need = @($s.pictures.missing_names | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) })
    if (-not $o.Need.Count) { $o.Action = "skip"; $o.Text = "all $($s.pictures.total) pictures are in $($s.pictures.dir)"; return $o }
    $o.InSrc = @(Get-NumberedPngs $o.Src | Where-Object { $o.Need -contains $_.BaseName })
    $all = @(Get-NumberedPngs $Downloads)
    $wanted = @($s.pictures.numbers | ForEach-Object { [string]$_ })
    $o.InDl = @($all | Where-Object { $o.Need -contains $_.BaseName })
    $o.Other = @($all | Where-Object { $wanted -notcontains $_.BaseName })
    if ($o.InDl.Count) {
        $o.Action = "move"
        $o.Text = "move $($o.InDl.Count) PNG(s) from Downloads to _YOUTUBE\$($o.Folder), convert to $($s.pictures.dir)"
    } elseif ($o.InSrc.Count) {
        $o.Action = "convert"
        $o.Text = "convert $($o.InSrc.Count) PNG(s) already in _YOUTUBE\$($o.Folder)"
    } else {
        $o.Action = "missing"
        $o.Text = "$($o.Need.Count) picture(s) missing ($(($o.Need | Select-Object -First 6) -join ', ')), and no such PNG in Downloads"
    }
    $left = @($o.Need | Where-Object { (@($o.InDl | ForEach-Object { $_.BaseName }) + @($o.InSrc | ForEach-Object { $_.BaseName })) -notcontains $_ })
    if ($o.Action -ne "missing" -and $left.Count) { $o.Text += "; still no PNG for $($left -join ', ')" }
    return $o
}

function Get-NextStep($s) {
    if (@($s.problems).Count) { return "fix the .md" }
    if (-not $s.exists) { return "1 lesson file" }
    if ($s.kind -eq "reader" -and $s.pictures.missing -gt 0) { return "2 pictures" }
    if (@($s.missing).Count) { return "3 audio" }
    if ($s.audio -ne "none" -and $s.pending) { return "4 upload" }
    if (-not $s.single_fresh) { return "5 offline copy" }
    return "done"
}

function Parse-Numbers($text) {
    $nums = @()
    foreach ($p in ($text -split '[\s,;]+')) { if ($p -match '^\d+$') { $nums += [int]$p } }
    return $nums
}

# ------------------------------------------------------------------ window
$form = New-Object System.Windows.Forms.Form
$form.Text = "Lesson app - from .md to lesson: pictures, audio, upload, offline copy"
$form.Size = New-Object System.Drawing.Size(1320, 900)
$form.MinimumSize = New-Object System.Drawing.Size(1280, 720)
$form.StartPosition = "CenterScreen"
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)
$form.AutoScaleMode = "Dpi"

$top = New-Object System.Windows.Forms.Panel
$top.Dock = "Top"; $top.Height = 44
$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = "Refresh"; $btnRefresh.Width = 90; $btnRefresh.Location = New-Object System.Drawing.Point(8, 8)
$chkTodo = New-Object System.Windows.Forms.CheckBox
$chkTodo.Text = "Only .md files with steps left"; $chkTodo.AutoSize = $true; $chkTodo.Location = New-Object System.Drawing.Point(112, 12)
$lblDirs = New-Object System.Windows.Forms.Label
$lblDirs.AutoSize = $true; $lblDirs.Location = New-Object System.Drawing.Point(340, 13)
$lblDirs.ForeColor = [System.Drawing.Color]::FromArgb(90, 90, 90)
$lblDirs.Text = ".md: $MdDir     new pictures: $Downloads"
$top.Controls.AddRange(@($btnRefresh, $chkTodo, $lblDirs))

$credit = New-Object System.Windows.Forms.Panel
$credit.Dock = "Top"; $credit.Height = 42
$credit.BackColor = [System.Drawing.Color]::FromArgb(232, 241, 255)
$btnCredits = New-Object System.Windows.Forms.Button
$btnCredits.Text = "Check balance"; $btnCredits.Width = 130; $btnCredits.Height = 30
$btnCredits.Location = New-Object System.Drawing.Point(8, 6)
$lblCredits = New-Object System.Windows.Forms.Label
$lblCredits.AutoSize = $true; $lblCredits.Location = New-Object System.Drawing.Point(150, 11)
$lblCredits.Font = New-Object System.Drawing.Font("Segoe UI", 10.5, [System.Drawing.FontStyle]::Bold)
$lblCredits.Text = "ElevenLabs balance: not checked yet"
$credit.Controls.AddRange(@($btnCredits, $lblCredits))

$list = New-Object System.Windows.Forms.ListView
$list.Dock = "Top"; $list.Height = 250
$list.View = "Details"; $list.FullRowSelect = $true; $list.MultiSelect = $false; $list.HideSelection = $false
[void]$list.Columns.Add(".md file", 210)
[void]$list.Columns.Add("Type", 100)
[void]$list.Columns.Add("Lesson", 290)
[void]$list.Columns.Add("Lesson file", 90)
[void]$list.Columns.Add("Pictures", 80)
[void]$list.Columns.Add("Audio", 80)
[void]$list.Columns.Add("Characters to make", 130)
[void]$list.Columns.Add("Online tag", 100)
[void]$list.Columns.Add("Offline copy", 110)
[void]$list.Columns.Add("Next step", 150)

function New-Row($title) {
    $r = New-Object System.Windows.Forms.FlowLayoutPanel
    $r.Dock = "Top"; $r.WrapContents = $false
    $r.AutoSize = $true; $r.AutoSizeMode = "GrowAndShrink"
    $r.Padding = New-Object System.Windows.Forms.Padding(6, 4, 6, 0)
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $title; $l.Width = 120; $l.Margin = New-Object System.Windows.Forms.Padding(4, 12, 4, 0)
    $l.Font = New-Object System.Drawing.Font("Segoe UI", 9.5, [System.Drawing.FontStyle]::Bold)
    $r.Controls.Add($l)
    return $r
}
function New-Button($row, $text, $width) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.AutoSize = $true; $b.MinimumSize = New-Object System.Drawing.Size($width, 32)
    $b.Margin = New-Object System.Windows.Forms.Padding(4)
    $row.Controls.Add($b)
    return $b
}
function New-Label($row, $text, $topMargin) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text; $l.AutoSize = $true; $l.Margin = New-Object System.Windows.Forms.Padding(4, $topMargin, 4, 0)
    $row.Controls.Add($l)
    return $l
}
function New-Text($row, $width) {
    $t = New-Object System.Windows.Forms.TextBox
    $t.Width = $width; $t.Margin = New-Object System.Windows.Forms.Padding(4, 9, 4, 4)
    $row.Controls.Add($t)
    return $t
}
function New-Combo($row, $width, $style) {
    $c = New-Object System.Windows.Forms.ComboBox
    $c.Width = $width; $c.DropDownStyle = $style; $c.Margin = New-Object System.Windows.Forms.Padding(4, 9, 4, 4)
    $row.Controls.Add($c)
    return $c
}

$rowAll = New-Row "All steps"
$btnAll = New-Button $rowAll "Run the remaining steps" 190
$btnAll.Font = New-Object System.Drawing.Font("Segoe UI", 9.5, [System.Drawing.FontStyle]::Bold)
$btnCheckMd = New-Button $rowAll "Check the .md" 120
$btnOpenMd = New-Button $rowAll "Open the .md" 110
$btnOpenJson = New-Button $rowAll "Open lesson file" 130
$btnFormats = New-Button $rowAll "The .md formats" 130
$btnStop = New-Button $rowAll "Stop" 80
$btnClear = New-Button $rowAll "Clear log" 90

$rowNew = New-Row "1  Lesson file"
[void](New-Label $rowNew "Name:" 12)
$txtName = New-Text $rowNew 170
[void](New-Label $rowNew "Level:" 12)
$cmbLevel = New-Combo $rowNew 80 "DropDownList"
[void](New-Label $rowNew "Topic:" 12)
$cmbTopic = New-Combo $rowNew 190 "DropDown"
[void](New-Label $rowNew "Picture folder:" 12)
$txtImages = New-Text $rowNew 160
$btnMake = New-Button $rowNew "Make lesson file" 130
$btnRemake = New-Button $rowNew "Remake from .md" 130

$rowPic = New-Row "2  Pictures"
$btnPictures = New-Button $rowPic "Move and convert pictures" 190
$btnOpenPics = New-Button $rowPic "Open picture folder" 150
$lblPic = New-Label $rowPic "" 12

$rowGen = New-Row "3  Audio"
$btnNext = New-Button $rowGen "Generate next" 120
$numNext = New-Object System.Windows.Forms.NumericUpDown
$numNext.Minimum = 1; $numNext.Maximum = 99; $numNext.Value = 1; $numNext.Width = 50
$numNext.Margin = New-Object System.Windows.Forms.Padding(2, 9, 2, 4)
$rowGen.Controls.Add($numNext)
[void](New-Label $rowGen "clip(s)" 12)
$btnGenAll = New-Button $rowGen "Generate all missing" 160
[void](New-Label $rowGen "    New takes of:" 12)
$txtRedo = New-Text $rowGen 120
$btnRedo = New-Button $rowGen "Make new takes" 130
$btnCheck = New-Button $rowGen "Whisper check all" 150
$btnFolder = New-Button $rowGen "Open clips folder" 140

$rowPub = New-Row "4-5  Publish"
$btnUpload = New-Button $rowPub "Upload to R2" 120
$btnOffline = New-Button $rowPub "Offline copy" 120
$btnOpenOffline = New-Button $rowPub "Open offline file" 140
$lblNext = New-Label $rowPub "Choose a .md file." 12
$lblNext.Font = New-Object System.Drawing.Font("Segoe UI", 9.5, [System.Drawing.FontStyle]::Italic)

$log = New-Object System.Windows.Forms.TextBox
$log.Dock = "Fill"; $log.Multiline = $true; $log.ReadOnly = $true; $log.ScrollBars = "Both"; $log.WordWrap = $false
$log.Font = New-Object System.Drawing.Font("Consolas", 9.5)
$log.BackColor = [System.Drawing.Color]::FromArgb(250, 250, 250)
$status = New-Object System.Windows.Forms.StatusStrip
$statusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$statusLabel.Text = "Ready"
[void]$status.Items.Add($statusLabel)

# docking order: Fill first, then Top controls from the lowest to the highest
$form.Controls.Add($log)
foreach ($c in @($rowPub, $rowGen, $rowPic, $rowNew, $rowAll, $list, $credit, $top, $status)) { $form.Controls.Add($c) }

function Write-Log($text) { $log.AppendText(($text -replace "`r?`n", "`r`n")) }
function Write-Line($text) { Write-Log ($text + "`r`n") }

# ------------------------------------------------------------------ list
$script:stories = @()
$script:proc = $null
$script:queue = @()

function Fill-List {
    $keep = $null
    if ($list.SelectedItems.Count) { $keep = $list.SelectedItems[0].Text }
    $statusLabel.Text = "Reading the .md files and the lessons..."
    [System.Windows.Forms.Application]::DoEvents()
    $script:stories = @(Get-Stories)
    $list.BeginUpdate()
    $list.Items.Clear()
    $todo = 0
    foreach ($s in $script:stories) {
        $next = Get-NextStep $s
        if ($next -ne "done") { $todo++ }
        if ($chkTodo.Checked -and $next -eq "done") { continue }
        $it = New-Object System.Windows.Forms.ListViewItem($s.md)
        [void]$it.SubItems.Add([string]$s.type)
        if (-not $s.id) {
            foreach ($x in "", "", "", "", "", "", "") { [void]$it.SubItems.Add($x) }
        } else {
            [void]$it.SubItems.Add([string]$s.id)
            [void]$it.SubItems.Add($(if ($s.exists) { "made" } else { "not made" }))
            [void]$it.SubItems.Add($(if ($s.pictures.total) { "$($s.pictures.total - $s.pictures.missing) / $($s.pictures.total)" } else { "" }))
            [void]$it.SubItems.Add($(if ($s.audio -eq "none") { "" } else { "$($s.total - @($s.missing).Count) / $($s.total)" }))
            [void]$it.SubItems.Add($(if ($s.chars) { "{0:N0}" -f $s.chars } else { "" }))
            [void]$it.SubItems.Add($(if ($s.audio -eq "none") { "" } elseif ($s.pending) { "not uploaded" } elseif ($s.tag) { [string]$s.tag } else { "online" }))
            if ($s.single_exists) {
                [void]$it.SubItems.Add($(if ($s.single_fresh) { (Get-Item -LiteralPath $s.single).LastWriteTime.ToString("yyyy-MM-dd") } else { "out of date" }))
            } else { [void]$it.SubItems.Add("") }
        }
        [void]$it.SubItems.Add($next)
        if ($next -eq "fix the .md") { $it.BackColor = [System.Drawing.Color]::FromArgb(253, 226, 226) }
        elseif ($next -eq "done") { $it.BackColor = [System.Drawing.Color]::FromArgb(224, 245, 228) }
        else { $it.BackColor = [System.Drawing.Color]::FromArgb(255, 241, 214) }
        $it.Tag = $s
        [void]$list.Items.Add($it)
        if ($keep -and $s.md -eq $keep) { $it.Selected = $true; $it.EnsureVisible() }
    }
    $list.EndUpdate()
    $statusLabel.Text = "$($script:stories.Count) lesson .md file(s), $todo with steps left.  Red = the .md has problems, amber = steps left, green = done."
    Update-Selection
}

function Get-Story($md) { return $script:stories | Where-Object { $_.md -eq $md } | Select-Object -First 1 }

function Get-Selected {
    if (-not $list.SelectedItems.Count) {
        [void][System.Windows.Forms.MessageBox]::Show("Choose a .md file in the list first.", "Lesson app")
        return $null
    }
    return $list.SelectedItems[0].Tag
}

function Get-Lesson {
    # the chosen story, when its lesson file exists
    $s = Get-Selected
    if (-not $s) { return $null }
    if (-not $s.exists) {
        [void][System.Windows.Forms.MessageBox]::Show("$($s.md) has no lesson file yet. Make it first (step 1).", "Lesson app")
        return $null
    }
    return $s
}

function Update-Selection {
    $s = $null
    if ($list.SelectedItems.Count) { $s = $list.SelectedItems[0].Tag }
    $cmbLevel.Items.Clear(); $cmbTopic.Items.Clear()
    if (-not $s -or -not $s.id) {
        $txtName.Text = ""; $txtImages.Text = ""; $cmbTopic.Text = ""; $lblPic.Text = ""
        $lblNext.Text = $(if ($s) { "$($s.md): " + (@($s.problems) | Select-Object -First 1) } else { "Choose a .md file in the list." })
    } else {
        foreach ($l in @($s.levels)) { [void]$cmbLevel.Items.Add($l) }
        foreach ($t in @($s.topics)) { [void]$cmbTopic.Items.Add($t) }
        $txtName.Text = [string]$s.name
        $cmbLevel.SelectedItem = [string]$s.level
        $cmbTopic.Text = [string]$s.topic
        $txtImages.Text = $(if ($s.kind -eq "reader" -and $s.pictures.dir) { ($s.pictures.dir.TrimEnd('/') -split '/')[-1] } else { "" })
        $lblPic.Text = (Get-PictureState $s).Text
        $n = @($s.missing).Count
        if (@($s.problems).Count) { $lblNext.Text = "$($s.md): $(@($s.problems).Count) problem(s) in the .md. Press Check the .md." }
        elseif ($s.audio -eq "none") { $lblNext.Text = "$($s.id): no clips of its own." }
        elseif (-not $n) { $lblNext.Text = "$($s.id): all $($s.total) clips are made." }
        else {
            $k = [string]@($s.missing)[0]
            $t = [string]$s.texts.$k
            $lblNext.Text = ('Next clip {0}: "{1}" = {2} characters. {3} missing in all.' -f $k, $t, $t.Length, $n)
        }
    }
    Update-Buttons
}

function Update-Buttons {
    $busy = $null -ne $script:proc
    $s = $null
    if ($list.SelectedItems.Count) { $s = $list.SelectedItems[0].Tag }
    $new = $s -and $s.id -and -not $s.exists
    foreach ($b in @($btnAll, $btnCheckMd, $btnMake, $btnRemake, $btnPictures, $btnNext, $numNext, $btnGenAll, $btnRedo, $btnCheck, $btnUpload, $btnOffline, $btnRefresh, $btnCredits)) { $b.Enabled = -not $busy }
    foreach ($c in @($txtName, $cmbLevel, $cmbTopic)) { $c.Enabled = (-not $busy) -and $new }      # only a new lesson is named here
    $txtImages.Enabled = (-not $busy) -and $new -and $s.kind -eq "reader"
    $btnMake.Enabled = (-not $busy) -and $new
    $btnRemake.Enabled = (-not $busy) -and $s -and $s.exists
    if ($s -and $s.audio -eq "words") { $btnNext.Enabled = $false; $numNext.Enabled = $false; $btnCheck.Enabled = $false }   # word lists are made in one go
    $btnStop.Enabled = $busy
}

# ------------------------------------------------------------------ running a job
$script:logFile = $null
$script:logPos = 0
$script:decoder = $null
$script:onDone = $null
$script:jobName = ""
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 300

function Start-Run($name, $cmdline, [scriptblock]$onDone) {
    $script:logFile = [IO.Path]::GetTempFileName()
    $script:logPos = 0
    $script:decoder = [Text.Encoding]::UTF8.GetDecoder()
    $script:onDone = $onDone
    $script:jobName = $name
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = '/d /s /c "' + $cmdline + ' > "' + $script:logFile + '" 2>&1"'
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    Write-Line ""
    Write-Line ("=== {0}  {1}" -f (Get-Date -Format "HH:mm:ss"), $name)
    Write-Line ("> " + $cmdline)
    $script:proc = [System.Diagnostics.Process]::Start($psi)
    $statusLabel.Text = "Running: $name"
    Update-Buttons
    $timer.Start()
}

function Read-NewLog {
    if (-not $script:logFile -or -not (Test-Path -LiteralPath $script:logFile)) { return }
    $fs = [IO.File]::Open($script:logFile, "Open", "Read", "ReadWrite")
    try {
        [void]$fs.Seek($script:logPos, "Begin")
        $buf = New-Object byte[] 65536
        while (($n = $fs.Read($buf, 0, $buf.Length)) -gt 0) {
            $script:logPos += $n
            $chars = New-Object char[] ($n + 4)
            $c = $script:decoder.GetChars($buf, 0, $n, $chars, 0)
            if ($c) { Write-Log (([string]::new($chars, 0, $c)) -replace "`r(?!`n)", "`n") }
        }
    } finally { $fs.Close() }
}

$timer.Add_Tick({
    Read-NewLog
    if ($script:proc -and $script:proc.HasExited) {
        $timer.Stop()
        Start-Sleep -Milliseconds 150
        Read-NewLog
        $code = $script:proc.ExitCode
        $name = $script:jobName
        $done = $script:onDone
        $script:proc = $null
        Remove-Item -LiteralPath $script:logFile -ErrorAction SilentlyContinue
        if ($code -eq 0) { Write-Line "=== done: $name" } else { Write-Line "=== FAILED (exit code $code): $name" }
        if ($done) { & $done $code }
        Fill-List
        $statusLabel.Text = $(if ($code -eq 0) { "Done: $name" } else { "Failed: $name (exit code $code)" })
        if ($script:queue.Count) {
            if ($code -ne 0) {
                Write-Line "=== stopped: the step failed, so the steps after it were not run."
                $script:queue = @()
            } else { Run-Queue }
        }
    }
})

$btnStop.Add_Click({
    $script:queue = @()
    if ($script:proc) {
        Write-Line "=== stopping..."
        & taskkill.exe /PID $script:proc.Id /T /F | Out-Null
    }
})

function Ask-YesNo($text) {
    $r = [System.Windows.Forms.MessageBox]::Show($text, "Lesson app",
        [System.Windows.Forms.MessageBoxButtons]::YesNo, [System.Windows.Forms.MessageBoxIcon]::Question)
    return $r -eq [System.Windows.Forms.DialogResult]::Yes
}

function Update-Credits {
    $key = Get-EnvVar "ELEVENLABS_API_KEY"
    if (-not $key) { $lblCredits.Text = "ElevenLabs balance: ELEVENLABS_API_KEY is not set"; return $null }
    try {
        $sub = Invoke-RestMethod -Uri "https://api.elevenlabs.io/v1/user/subscription" -Headers @{ "xi-api-key" = $key } -TimeoutSec 20
        $left = [int64]$sub.character_limit - [int64]$sub.character_count
        $reset = ""
        if ($sub.next_character_count_reset_unix) {
            $reset = "   (resets " + ([DateTimeOffset]::FromUnixTimeSeconds([int64]$sub.next_character_count_reset_unix).LocalDateTime.ToString("yyyy-MM-dd")) + ")"
        }
        $lblCredits.Text = ("ElevenLabs balance: {0:N0} characters left of {1:N0}{2}   - checked {3:HH:mm}" -f $left, [int64]$sub.character_limit, $reset, (Get-Date))
        $script:creditsLeft = $left
        return $left
    } catch {
        $lblCredits.Text = "ElevenLabs balance: could not read it (" + $_.Exception.Message + ")"
        return $null
    }
}
$script:creditsLeft = $null

# ------------------------------------------------------------------ the steps
# Each step sets $script:r:  "run" = a job was started,  "skip" = nothing to do,  "stop" = cannot go on.
# $auto is true inside "Run the remaining steps": the plan was confirmed once, so the steps do not ask again.
$script:made = $false       # this run made or changed something, so upload and offline copy are not skipped

function Step-Lesson($s, $auto, $force) {
    if (@($s.problems).Count) {
        Write-Line "$($s.md) has $(@($s.problems).Count) problem(s):"
        foreach ($p in @($s.problems)) { Write-Line "   $p" }
        $script:r = "stop"; return
    }
    if ($s.exists -and -not $force) {
        Write-Line "1 lesson file: SKIPPED, $($s.id) is already made."
        $script:r = "skip"; return
    }
    $cmd = "python -E tools\from_md.py make " + (Quote $s.path) + " --md " + (Quote $MdDir) + " --yt " + (Quote $YouTube)
    if ($force) { $cmd += " --force" }
    else {
        if ($txtName.Text.Trim()) { $cmd += " --name " + (Quote $txtName.Text.Trim()) }
        if ($cmbLevel.SelectedItem) { $cmd += " --level " + (Quote $cmbLevel.SelectedItem) }
        if ($cmbTopic.Text.Trim()) { $cmd += " --topic " + (Quote $cmbTopic.Text.Trim()) }
        if ($txtImages.Text.Trim() -and $s.kind -eq "reader") { $cmd += " --images " + (Quote $txtImages.Text.Trim()) }
    }
    $script:made = $true
    Start-Run "1 lesson file: $($s.md)" $cmd $null
    $script:r = "run"
}

function Step-Pictures($s, $auto) {
    $p = Get-PictureState $s
    if (-not $p.Applies) { Write-Line "2 pictures: SKIPPED, $($p.Text)."; $script:r = "skip"; return }
    if ($p.Action -eq "skip") {
        Write-Line "2 pictures: SKIPPED, $($p.Text)."
        $n = @(Get-NumberedPngs $Downloads).Count
        if ($n) { Write-Line "   ($n numbered PNG(s) in Downloads were left alone.)" }
        $script:r = "skip"; return
    }
    if ($p.Action -eq "missing") { Write-Line "2 pictures: NOT DONE, $($p.Text). The page shows a placeholder for them."; $script:r = "skip"; return }
    if (-not (Test-Path -LiteralPath $YouTube)) { Write-Line "2 pictures: can't find $YouTube. Is Google Drive running?"; $script:r = "stop"; return }
    if ($p.Action -eq "move") {
        if (-not $auto) {
            $msg = "Move these PNGs from Downloads to`n$($p.Src)`nand convert them to JPG in`n$($p.Out) ?`n`n" + (($p.InDl | ForEach-Object { $_.Name }) -join "  ")
            if ($p.Other.Count) { $msg += "`n`nLeft in Downloads (not pictures of this story): " + (($p.Other | ForEach-Object { $_.Name }) -join "  ") }
            if (-not (Ask-YesNo $msg)) { $script:r = "stop"; return }
        }
        New-Item -ItemType Directory -Path $p.Src -Force | Out-Null
        $moved = 0
        foreach ($f in $p.InDl) {
            $dest = Join-Path $p.Src $f.Name
            if (Test-Path -LiteralPath $dest) { Write-Line "KEEP  $($f.Name)  - already in the _YOUTUBE folder, left in Downloads" }
            else { Move-Item -LiteralPath $f.FullName -Destination $dest; $moved++ }
        }
        Write-Line ""
        Write-Line "Moved $moved PNG(s) to $($p.Src)"
    }
    $script:made = $true
    # convert.py leaves JPGs that are already there alone
    Start-Run "2 pictures: $($s.md)" ("python tools\convert.py " + (Quote $p.Src) + " --scale 0.8 -o " + (Quote $p.Out)) $null
    $script:r = "run"
}

function Start-Generate($s, $cmd, $name) {
    $script:genBefore = Update-Credits
    $script:made = $true
    Start-Run $name $cmd {
        param($code)
        $before = $script:genBefore
        $left = Update-Credits
        if ($null -ne $before -and $null -ne $left) {
            Write-Line ("ElevenLabs: {0:N0} characters used by this run, {1:N0} left." -f ($before - $left), $left)
        }
    }
}

function Step-Audio($s, $auto) {
    if ($s.audio -eq "none") { Write-Line "3 audio: SKIPPED, this lesson has no clips of its own."; $script:r = "skip"; return }
    $miss = @($s.missing)
    if (-not $miss.Count) { Write-Line "3 audio: SKIPPED, all $($s.total) clips are made."; $script:r = "skip"; return }
    if (-not $auto) {
        $msg = "Generate all $($miss.Count) missing clip(s) of $($s.id) with ElevenLabs?`n`nAbout $("{0:N0}" -f $s.chars) characters of credit"
        if ($null -ne $script:creditsLeft) { $msg += "; $("{0:N0}" -f $script:creditsLeft) left" }
        $msg += ".`nThe new clips are leveled and checked with Whisper."
        if ($null -ne $script:creditsLeft -and $s.chars -gt $script:creditsLeft) { $msg += "`n`nWARNING: that is more than the balance." }
        if (-not (Ask-YesNo $msg)) { $script:r = "stop"; return }
    }
    if ($s.audio -eq "words") { Start-Generate $s "python -E tools\audio.py words $($s.id)" "3 audio (words): $($s.id)" }
    else { Start-Generate $s ("python -E tools\audio.py make $($s.id) --only " + ($miss -join " ")) "3 audio ($($miss.Count) clips): $($s.id)" }
    $script:r = "run"
}

function Step-Upload($s, $auto) {
    if ($s.audio -eq "none") { Write-Line "4 upload: SKIPPED, this lesson has no clips of its own."; $script:r = "skip"; return }
    if (@($s.missing).Count) {
        Write-Line "4 upload: NOT DONE, $(@($s.missing).Count) clip(s) are still missing."
        $script:r = "stop"; return
    }
    if ($auto -and -not $s.pending -and -not $script:made) {
        Write-Line "4 upload: SKIPPED, the clips are online$(if ($s.tag) { " (tag $($s.tag))" }) and this run made no new ones."
        $script:r = "skip"; return
    }
    if (-not $auto) {
        if (-not (Ask-YesNo "Upload the clips of $($s.id) to R2 (bucket languages)?`n`nOnly new or changed clips are sent.")) { $script:r = "stop"; return }
    }
    $script:made = $true
    Start-Run "4 upload: $($s.id)" "python -E tools\audio.py upload $($s.id)" $null
    $script:r = "run"
}

function Step-Offline($s, $auto) {
    if ($auto -and $s.single_fresh -and -not $script:made) {
        Write-Line "5 offline copy: SKIPPED, $([IO.Path]::GetFileName($s.single)) is up to date."
        $script:r = "skip"; return
    }
    if (-not $auto -and @($s.missing).Count) {
        if (-not (Ask-YesNo "$($s.id) is missing $(@($s.missing).Count) clip(s). The offline copy embeds the clips, so those would be silent.`n`nBuild it anyway?")) { $script:r = "stop"; return }
    }
    $script:offlineFile = $s.single
    Start-Run "5 offline copy: $($s.id)" "python -E tools\offline.py $($s.id)" {
        param($code)
        if (Test-Path -LiteralPath $script:offlineFile) {
            $fi = Get-Item -LiteralPath $script:offlineFile
            Write-Line ("Offline copy: {0}  ({1:N1} MB, {2:HH:mm:ss})" -f $fi.FullName, ($fi.Length / 1MB), $fi.LastWriteTime)
        }
    }
    $script:r = "run"
}

function Run-Queue {
    while ($script:queue.Count) {
        $step = $script:queue[0]
        $script:queue = @($script:queue | Select-Object -Skip 1)
        $s = Get-Story $script:queueMd                     # the list was read again after the last job
        if (-not $s -or -not $s.id) { Write-Line "=== stopped: $($script:queueMd) can no longer be read."; $script:queue = @(); return }
        if ($step -ne "Lesson" -and -not $s.exists) { Write-Line "=== stopped: the lesson file was not made."; $script:queue = @(); return }
        $script:r = "skip"
        switch ($step) {
            "Lesson" { Step-Lesson $s $true $false }
            "Pictures" { Step-Pictures $s $true }
            "Audio" { Step-Audio $s $true }
            "Upload" { Step-Upload $s $true }
            "Offline" { Step-Offline $s $true }
        }
        if ($script:r -eq "stop") { Write-Line "=== stopped at this step."; $script:queue = @(); Update-Buttons; return }
        if ($script:r -eq "run") { return }               # the timer calls Run-Queue again when the job is done
    }
    Write-Line ("=== {0}  all steps done for {1}. To put the page on the website: 5_publish.bat" -f (Get-Date -Format "HH:mm:ss"), $script:queueMd)
    Update-Buttons
}

function Get-Plan($s) {
    # what "Run the remaining steps" will do, as text for the confirmation
    $lines = @()
    $lines += $(if ($s.exists) { "1  Lesson file:   skip, already made ($($s.id))" } else { "1  Lesson file:   MAKE content\$($s.course)\$($s.strand)\$($txtName.Text.Trim()).json  (level $($cmbLevel.SelectedItem), topic '$($cmbTopic.Text.Trim())')" })
    $p = Get-PictureState $s
    $lines += $(if (-not $p.Applies) { "2  Pictures:      skip, none for this kind of lesson" }
        elseif ($p.Action -eq "skip") { "2  Pictures:      skip, $($p.Text)" }
        elseif ($p.Action -eq "missing") { "2  Pictures:      NOT POSSIBLE, $($p.Text)" }
        else { "2  Pictures:      " + $p.Text.Substring(0, 1).ToUpper() + $p.Text.Substring(1) })
    if ($p.Action -eq "move") {
        $lines += "                  PNGs: " + (($p.InDl | ForEach-Object { $_.Name }) -join " ")
        if ($p.Other.Count) { $lines += "                  left in Downloads: " + (($p.Other | ForEach-Object { $_.Name }) -join " ") }
    }
    $n = @($s.missing).Count
    if ($s.audio -eq "none") { $lines += "3  Audio:         skip, no clips of its own"; $lines += "4  Upload:        skip" }
    else {
        if ($n) {
            $a = "3  Audio:         GENERATE $n clip(s) with ElevenLabs, about $("{0:N0}" -f $s.chars) characters"
            if ($null -ne $script:creditsLeft) { $a += " ($("{0:N0}" -f $script:creditsLeft) left)" }
            $lines += $a
            if ($null -ne $script:creditsLeft -and $s.chars -gt $script:creditsLeft) { $lines += "                  WARNING: that is more than the balance." }
        } else { $lines += "3  Audio:         skip, all $($s.total) clips are made" }
        $lines += $(if ($n -or $s.pending -or -not $s.exists) { "4  Upload:        UPLOAD the clips to R2 and set the ?v= tag" } else { "4  Upload:        skip, already online$(if ($s.tag) { " (tag $($s.tag))" })" })
    }
    $work = (-not $s.exists) -or $n -or $s.pending -or ($p.Action -in "move", "convert")
    $lines += $(if ($work -or -not $s.single_fresh) { "5  Offline copy:  BUILD $([IO.Path]::GetFileName($s.single))" } else { "5  Offline copy:  skip, up to date" })
    return $lines
}

# ------------------------------------------------------------------ buttons
$btnAll.Add_Click({
    $s = Get-Selected; if (-not $s) { return }
    if (-not $s.id -or @($s.problems).Count) { $script:r = ""; Step-Lesson $s $false $false; if (-not @($s.problems).Count) { Write-Line "$($s.md): $($lblNext.Text)" }; return }
    [void](Update-Credits)
    $plan = Get-Plan $s
    if (-not ($plan | Where-Object { $_ -cmatch 'MAKE|GENERATE|UPLOAD|BUILD|Move|Convert' })) {
        Write-Line ""
        Write-Line "$($s.md): nothing left to do."
        foreach ($l in $plan) { Write-Line "   $l" }
        return
    }
    if (-not (Ask-YesNo ("Run these steps for $($s.md)?`n`n" + ($plan -join "`n")))) { return }
    $script:made = $false
    $script:queueMd = $s.md
    $script:queue = @("Lesson", "Pictures", "Audio", "Upload", "Offline")
    Write-Line ""
    Write-Line ("=== {0}  remaining steps for {1}" -f (Get-Date -Format "HH:mm:ss"), $s.md)
    Run-Queue
})

$btnCheckMd.Add_Click({
    $s = Get-Selected; if (-not $s) { return }
    Start-Run "check: $($s.md)" ("python -E tools\from_md.py check " + (Quote $s.path) + " --md " + (Quote $MdDir) + " --yt " + (Quote $YouTube)) $null
})

$btnOpenMd.Add_Click({
    $s = Get-Selected; if (-not $s) { return }
    Start-Process -FilePath "notepad.exe" -ArgumentList (Quote $s.path)
})

$btnFormats.Add_Click({
    # the description at the top of tools\from_md.py
    $src = [IO.File]::ReadAllText((Join-Path $Root "tools\from_md.py"), [Text.Encoding]::UTF8)
    $m = [regex]::Match($src, '(?s)^"""(.*?)"""')
    Write-Line ""
    Write-Line $m.Groups[1].Value
})

$btnMake.Add_Click({
    $s = Get-Selected; if (-not $s) { return }
    $script:made = $false
    Step-Lesson $s $false $false
})

$btnRemake.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    $msg = "Replace the text of $($s.id) with what is in $($s.md)?`n`nLevel, topic, the audio tag and anything else set by hand are kept."
    if ($s.audio -ne "none") { $msg += "`nClips are NOT made again: if a sentence changed, the log lists the clips that need a new take." }
    if (-not (Ask-YesNo $msg)) { return }
    Step-Lesson $s $false $true
})

$btnOpenJson.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    Start-Process -FilePath "notepad.exe" -ArgumentList (Quote $s.lesson_file)
})

$btnPictures.Add_Click({
    $s = Get-Selected; if (-not $s -or -not $s.id) { return }
    Write-Line ""
    Step-Pictures $s $false
})

$btnOpenPics.Add_Click({
    $s = Get-Selected; if (-not $s -or -not $s.id) { return }
    $p = Get-PictureState $s
    if ($p.Out -and (Test-Path -LiteralPath $p.Out)) { Start-Process explorer.exe -ArgumentList (Quote $p.Out) }
    else { [void][System.Windows.Forms.MessageBox]::Show("No picture folder yet$(if ($p.Out) { ": $($p.Out)" }).", "Lesson app") }
})

$btnNext.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    if ($s.audio -ne "clips") { [void][System.Windows.Forms.MessageBox]::Show("$($s.id) has no numbered clips of its own.", "Lesson app"); return }
    $miss = @($s.missing)
    if (-not $miss.Count) { [void][System.Windows.Forms.MessageBox]::Show("$($s.id) has all $($s.total) clips. Use New takes to re-record single clips.", "Lesson app"); return }
    $nums = @($miss | Select-Object -First ([int]$numNext.Value))
    $chars = 0
    foreach ($n in $nums) { $chars += ([string]$s.texts.([string]$n)).Length }
    if ($nums.Count -gt 1 -or ($null -ne $script:creditsLeft -and $chars -gt $script:creditsLeft)) {
        $msg = "Generate clip(s) $($nums -join ', ') of $($s.id) with ElevenLabs?`n`nAbout $chars characters"
        if ($null -ne $script:creditsLeft) { $msg += "; $("{0:N0}" -f $script:creditsLeft) left." } else { $msg += "." }
        if ($null -ne $script:creditsLeft -and $chars -gt $script:creditsLeft) { $msg += "`n`nWARNING: that is more than the balance." }
        if (-not (Ask-YesNo $msg)) { return }
    }
    Start-Generate $s ("python -E tools\audio.py make $($s.id) --only " + ($nums -join " ")) "generate $($nums -join ' '): $($s.id)"
})

$btnGenAll.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    Write-Line ""
    Step-Audio $s $false
})

$btnRedo.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    if ($s.audio -eq "none") { [void][System.Windows.Forms.MessageBox]::Show("$($s.id) has no clips of its own.", "Lesson app"); return }
    if ($s.audio -eq "words") {
        $names = @($txtRedo.Text -split '[\s,;]+' | Where-Object { $_ } | ForEach-Object { if ($_ -like "*.mp3") { $_ } else { "$_.mp3" } })
        if (-not $names.Count) { [void][System.Windows.Forms.MessageBox]::Show("Type the clip files to re-record, e.g. maison.mp3 toit.mp3 (see the clips folder).", "Lesson app"); return }
        if (-not (Ask-YesNo "Make new takes of $($names -join ', ') for $($s.id)?`n`nThe old clips are moved aside, not deleted.")) { return }
        Start-Generate $s ("python -E tools\audio.py words $($s.id) --redo " + (($names | ForEach-Object { Quote $_ }) -join " ")) "new takes: $($s.id)"
        return
    }
    $nums = @(Parse-Numbers $txtRedo.Text | Where-Object { $_ -ge 1 -and $_ -le $s.total })
    if (-not $nums.Count) { [void][System.Windows.Forms.MessageBox]::Show("Type the clip numbers to re-record, e.g. 6 12 30 (1 to $($s.total)).", "Lesson app"); return }
    if (-not (Ask-YesNo "Make new takes of clip(s) $($nums -join ', ') for $($s.id)?`n`nThe old clips and raw takes are moved aside, not deleted.")) { return }
    Start-Generate $s ("python -E tools\audio.py make $($s.id) --redo " + ($nums -join " ")) "new takes $($nums -join ' '): $($s.id)"
})

$btnCheck.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    if ($s.audio -ne "clips" -or @($s.missing).Count -eq $s.total) { [void][System.Windows.Forms.MessageBox]::Show("$($s.id) has no numbered clips to check yet.", "Lesson app"); return }
    Write-Line ""
    Write-Line "Whisper is transcribing the clips; this can take a few minutes."
    Start-Run "Whisper check: $($s.id)" "python -E tools\audio.py check $($s.id)" $null
})

$btnFolder.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    if ($s.media -and (Test-Path -LiteralPath $s.media)) { Start-Process explorer.exe -ArgumentList (Quote $s.media) }
    else { [void][System.Windows.Forms.MessageBox]::Show("No clips folder yet: $($s.media)", "Lesson app") }
})

$btnUpload.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    Write-Line ""
    Step-Upload $s $false
})

$btnOffline.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    Write-Line ""
    Step-Offline $s $false
})

$btnOpenOffline.Add_Click({
    $s = Get-Lesson; if (-not $s) { return }
    if (Test-Path -LiteralPath $s.single) { Start-Process -FilePath $s.single }
    else { [void][System.Windows.Forms.MessageBox]::Show("No offline copy yet: $($s.single)", "Lesson app") }
})

$btnClear.Add_Click({ $log.Clear() })
$btnCredits.Add_Click({ [void](Update-Credits) })
$btnRefresh.Add_Click({ Fill-List })
$chkTodo.Add_CheckedChanged({ Fill-List })
$list.Add_SelectedIndexChanged({ Update-Selection })

$form.Add_FormClosing({
    if ($script:proc) {
        if (-not (Ask-YesNo "A job is still running. Stop it and close?")) { $_.Cancel = $true; return }
        & taskkill.exe /PID $script:proc.Id /T /F | Out-Null
    }
})

# self-test (LESSON_APP_SELFTEST=<file>): list the .md files, write the plan of each, close. No audio, no network, nothing written.
if ($env:LESSON_APP_SELFTEST) {
    $form.Add_Shown({
        $out = @("md folder: $MdDir", "rows: $($list.Items.Count)")
        foreach ($it in @($list.Items)) {
            $it.Selected = $true
            $s = $it.Tag
            $out += ""
            $out += (($it.SubItems | ForEach-Object { $_.Text }) -join " | ")
            $out += "  fields: name '$($txtName.Text)' level '$($cmbLevel.SelectedItem)' topic '$($cmbTopic.Text)' pictures '$($txtImages.Text)'  make enabled: $($btnMake.Enabled)"
            $out += "  next: $($lblNext.Text)"
            $out += "  pictures: $($lblPic.Text)"
            if ($s.id -and -not @($s.problems).Count) { foreach ($l in (Get-Plan $s)) { $out += "  plan: $l" } }
            else { foreach ($p in @($s.problems)) { $out += "  problem: $p" } }
        }
        $hidden = @()
        foreach ($r in $rowAll, $rowNew, $rowPic, $rowGen, $rowPub) { foreach ($c in $r.Controls) { if ($c.Right -gt $r.ClientSize.Width -or $c.Bottom -gt $r.ClientSize.Height) { $hidden += "$($c.GetType().Name) '$($c.Text)'" } } }
        $out += ""
        $out += "controls outside their row: " + $(if ($hidden.Count) { $hidden -join ", " } else { "none" })
        $out += "log: " + $log.Text
        [IO.File]::WriteAllLines($env:LESSON_APP_SELFTEST, $out, $Utf8NoBom)
        $form.Close()
    })
} else {
    $form.Add_Shown({ [void](Update-Credits) })
}

Write-Line "Choose a .md file. 'Run the remaining steps' does everything that is left for it and skips what is already done;"
Write-Line "the numbered rows run one step at a time. ElevenLabs and R2 keys come from your User environment variables."
Fill-List
[void]$form.ShowDialog()
