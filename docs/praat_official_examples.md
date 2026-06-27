# Praat 공식 스크립트 예제 모음

출처: [praat/praat.github.io](https://github.com/praat/praat.github.io) (Praat 개발자 공식 저장소) `docs/manual/Scripting_examples.html` 및 관련 페이지.
새 분석 스크립트를 작성하거나 기존 스크립트의 명령/문법을 검증할 때 1차 참고 자료로 사용.

## 1. Script for listing time–F0 pairs

시간-피치 쌍 목록 출력. 무성 구간은 피치 칸을 비워둠.

```praat
writeInfoLine: "Time:    Pitch:"
numberOfFrames = Get number of frames
for iframe to numberOfFrames
   time = Get time from frame: iframe
   pitch = Get value in frame: iframe, "Hertz"
   if pitch = undefined
      appendInfoLine: fixed$ (time, 6)
   else
      appendInfoLine: fixed$ (time, 6), " ", fixed$ (pitch, 3)
   endif
endfor
```

Info 창 대신 파일로 쓰려면:

```praat
appendFile: "out.txt", info$ ( )
```

(선행 조건: Pitch 객체가 선택된 상태)

## 2. Script for listing time–F0–intensity

Pitch와 Intensity의 시간 해상도가 다르므로, 둘 다 높은 시간 해상도로 만든 뒤 보간(interpolate)해서 같은 시각의 값을 뽑는다.

```praat
sound = selected ("Sound")
tmin = Get start time
tmax = Get end time
To Pitch: 0.001, 75, 300
Rename: "pitch"
selectObject: sound
To Intensity: 75, 0.001
Rename: "intensity"
writeInfoLine: "Here are the results:"
for i to (tmax-tmin)/0.01
   time = tmin + i * 0.01
   selectObject: "Pitch pitch"
   pitch = Get value at time: time, "Hertz", "linear"
   selectObject: "Intensity intensity"
   intensity = Get value at time: time, "cubic"
   appendInfoLine: fixed$ (time, 2), " ", fixed$ (pitch, 3), " ", fixed$ (intensity, 3)
endfor
```

## 3. Script for listing F0 statistics

50ms 구간별로 평균/최소/최대/표준편차 F0를 구함. (Sound 전체에 `To Pitch...` 적용 후 구간별 query — 짧은 조각마다 따로 `To Pitch`를 하면 가장자리 20ms가 분석 누락되므로 금지.)

```praat
startTime = Get start time
endTime = Get end time
numberOfTimeSteps = (endTime - startTime) / 0.05
writeInfoLine: "   tmin     tmax    mean   fmin   fmax  stdev"
for step to numberOfTimeSteps
   tmin = startTime + (step - 1) * 0.05
   tmax = tmin + 0.05
   mean = Get mean: tmin, tmax, "Hertz"
   minimum = Get minimum: tmin, tmax, "Hertz", "Parabolic"
   maximum = Get maximum: tmin, tmax, "Hertz", "Parabolic"
   stdev = Get standard deviation: tmin, tmax, "Hertz"
   appendInfoLine: fixed$ (tmin, 6), " ", fixed$ (tmax, 6), " ", fixed$ (mean, 2),
   ... " ", fixed$ (minimum, 2), " ", fixed$ (maximum, 2), " ", fixed$ (stdev, 2)
endfor
```

파일로 출력 시:

```praat
deleteFile: "~/results/out.txt"
appendFileLine: "~/results/out.txt ", fixed$ (tmin, 6), " ", fixed$ (tmax, 6), " ",
... fixed$ (mean, 2), " ", fixed$ (minimum, 2), " ", fixed$ (maximum, 2), " ",
... fixed$ (stdev, 2)
```

## 4. Script for creating a frequency sweep

1kHz→12kHz로 60초간 스윕하면서 진폭도 선형으로 증가시키는 사인파 생성.

```praat
Create Sound from formula: "sweep", 1, 0, 60, 44100,
... ~ 0.05 * (1 + 11 * x/60) * sin (2*pi * (1000 + 11000/2 * x/60) * x)
```

수식 유도: frequency(t) = 1000 + 11000·t/60, phase(t) = ∫frequency(t)dt, signal(t) = sin(phase(t)). 적분 때문에 `11000/2`가 들어감 (1/2가 누락되기 쉬운 실수 포인트).

## 5. Script for onset detection

Intensity 컨투어에서 특정 임계값(예: 40dB)을 넘는 첫 프레임을 찾아 음성 시작 시점으로 판단.

```praat
To Intensity: 100, 0
n = Get number of frames
for i to n
   intensity = Get value in frame: i
   if intensity > 40
      time = Get time from frame: i
      writeInfoLine: "Onset of sound at: ", fixed$ (time, 3), " seconds."
      exit
   endif
endfor
```

주의: Intensity는 윈도우가 길어서 실제 시작보다 0.01~0.02초 늦게 잡힐 수 있음.

## 6. Script for TextGrid boundary drawing

TextGrid의 경계선만(라벨 텍스트 없이) 다른 분석 그림 위에 점선으로 표시.

```praat
n = Get number of intervals: 1
for i to n-1
   t = Get end point: 1, i
   One mark bottom: t, "no", "no", "yes"
endfor
```

## 7. Script for analysing pitch with a TextGrid

TextGrid 5번 tier에서 라벨이 비어있지 않은 구간만 평균 피치를 구해서 출력.

```praat
if numberOfSelected ("Sound") <> 1 or numberOfSelected ("TextGrid") <> 1
   exitScript: "Please select a Sound and a TextGrid first."
endif
sound = selected ("Sound")
textgrid = selected ("TextGrid")
writeInfoLine: "Result:"
selectObject: sound
pitch = To Pitch: 0.0, 75, 600
selectObject: textgrid
n = Get number of intervals: 5
for i to n
   tekst$ = Get label of interval: 5, i
   if tekst$ <> ""
      t1 = Get starting point: 5, i
      t2 = Get end point: 5, i
      selectObject: pitch
      f0 = Get mean: t1, t2, "Hertz"
      appendInfoLine: fixed$ (t1, 3), " ", fixed$ (t2, 3), " ", round (f0), " ", tekst$
      selectObject: textgrid
   endif
endfor
selectObject: sound, textgrid
```

## 8. Voice 6. Automating voice analysis with a script

GUI 없이(Objects 창에서만) jitter/shimmer/voice report를 뽑는 공식 가이드.

- **Pulses(PointProcess) 만드는 법**: `Sound: To PointProcess (periodic, cc)...` 한 번에 만들거나, `Sound: To Pitch (raw cc)...` → `Sound & Pitch: To PointProcess (cc)` 두 단계로. 음성 분석(jitter/shimmer) 목적이면 cross-correlation(cc) 기반이 권장됨. `Pitch: To PointProcess` 단독 사용은 금지 — 펄스가 Sound의 실제 주기와 정렬되지 않음.
- **Jitter/Shimmer**: PointProcess 선택 후 Query submenu의 `Get jitter...` / (Sound와 함께 선택 후) `Get shimmer...` 명령 사용.
- **Voice report 전체**: Sound + Pitch + PointProcess 세 개를 함께 선택하면 `Voice report...` 버튼이 생김. 스크립트에서는:

```praat
voiceReport$ = Voice report: 0, 0, 75, 500, 1.3, 1.6, 0.03, 0.45
jitter = extractNumber (voiceReport$, "Jitter (local): ")
shimmer = extractNumber (voiceReport$, "Shimmer (local): ")
writeInfoLine: "Jitter = ", percent$ (jitter, 3), ", shimmer = ", percent$ (shimmer, 3)
```

- **한계**: 시간 범위(0.0, 0.0 = 전체)를 사람이 직접 판단해서 넣어야 함. GUI에서는 보고 싶은 구간을 직접 선택하지만, 스크립트는 자동으로 무음/오류 구간을 걸러내지 못함 — 배치 스크립트 작성 시 `totDur > 0.1` 같은 최소 길이 체크나 무음 구간 트리밍이 필요한 이유.
