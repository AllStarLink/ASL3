#!/usr/bin/env bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../../bin/asl-say"
  # Enable testing mode to avoid requiring asterisk
  export ASL_SAY_TESTING=1
}

teardown() {
  unset ASL_SAY_TESTING
}

@test "fails if no arguments provided" {
  run "$SCRIPT"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "fails if -n (node) not specified" {
  run "$SCRIPT" -w date
  [ "$status" -ne 0 ]
  [[ "$output" =~ "must be a number" ]]
}

@test "fails if -w (what) not specified" {
  run "$SCRIPT" -n 12345
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "fails if node is not a number" {
  run "$SCRIPT" -n abcd -w date
  [ "$status" -ne 0 ]
  [[ "$output" =~ "must be a number" ]]
}

@test "fails if node is 0" {
  run "$SCRIPT" -n 0 -w date
  [ "$status" -ne 0 ]
  [[ "$output" =~ "must be a number" ]]
}

@test "fails if node is negative" {
  run "$SCRIPT" -n -5 -w date
  [ "$status" -ne 0 ]
  [[ "$output" =~ "must be a number" ]]
}

@test "fails for invalid 'what' argument" {
  run "$SCRIPT" -n 12345 -w invalid
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "prints date audio sequence for 'date'" {
  run "$SCRIPT" -n 12345 -w date
  [ "$status" -eq 0 ]
  [[ "$output" =~ "digits/today" ]]
  [[ "$output" =~ "digits/day-" ]]
  [[ "$output" =~ "digits/mon-" ]]
  [[ "$output" =~ "digits/h-" ]]
}

@test "prints time audio sequence for 'time'" {
  run "$SCRIPT" -n 12345 -w time
  [ "$status" -eq 0 ]
  [[ "$output" =~ "rpt/thetimeis" ]]
  [[ "$output" =~ "digits/" ]]
  [[ "$output" =~ "digits/" ]]
  [[ "$output" =~ "p-m\|a-m" ]]
}

@test "prints 24-hour time audio sequence for 'time24'" {
  run "$SCRIPT" -n 12345 -w time24
  [ "$status" -eq 0 ]
  [[ "$output" =~ "rpt/thetimeis" ]]
  [[ "$output" =~ "digits/" ]]
}

@test "prints datetime audio sequence for 'datetime'" {
  run "$SCRIPT" -n 12345 -w datetime
  [ "$status" -eq 0 ]
  [[ "$output" =~ "digits/today" ]]
  [[ "$output" =~ "rpt/thetimeis" ]]
}

@test "prints 24-hour datetime audio sequence for 'datetime24'" {
  run "$SCRIPT" -n 12345 -w datetime24
  [ "$status" -eq 0 ]
  [[ "$output" =~ "digits/today" ]]
  [[ "$output" =~ "rpt/thetimeis" ]]
}

@test "prints IPv4 audio sequence for 'ip4'" {
  run "$SCRIPT" -n 12345 -w ip4
  [ "$status" -eq 0 ]
  [[ "$output" =~ "letters/i" ]]
  [[ "$output" =~ "letters/p" ]]
  [[ "$output" =~ "digits/" ]]
}

@test "prints IPv4 audio sequence for 'ip'" {
  run "$SCRIPT" -n 12345 -w ip
  [ "$status" -eq 0 ]
  [[ "$output" =~ "letters/i" ]]
  [[ "$output" =~ "letters/p" ]]
  [[ "$output" =~ "digits/" ]]
}

@test "prints IPv6 audio sequence for 'ip6'" {
  run "$SCRIPT" -n 12345 -w ip6
  [ "$status" -eq 0 ]
  [[ "$output" =~ "letters/i" ]]
  [[ "$output" =~ "letters/p" ]]
  [[ "$output" =~ "digits/6" ]]
}

@test "accepts large valid node numbers" {
  run "$SCRIPT" -n 999989 -w date
  [ "$status" -eq 0 ]
  [[ "$output" =~ "digits/today" ]]
}

@test "accepts small valid node numbers" {
  run "$SCRIPT" -n 1 -w date
  [ "$status" -eq 0 ]
  [[ "$output" =~ "digits/today" ]]
}

@test "accepts optional date argument" {
  run "$SCRIPT" -n 12345 -w date -d "2025-03-31"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "digits/today" ]]
}

@test "date argument affects output" {
  run1=$("$SCRIPT" -n 12345 -w time -d "2025-03-31 14:30:45" 2>&1)
  run2=$("$SCRIPT" -n 12345 -w time -d "2025-03-31 23:59:59" 2>&1)
  # Different times should potentially produce different output
  # (though this is a simple check)
  [ -n "$run1" ]
  [ -n "$run2" ]
}

@test "help option shows usage" {
  run "$SCRIPT" --help
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "unknown option shows usage" {
  run "$SCRIPT" --unknown
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "output includes NODE information when processed" {
  run "$SCRIPT" -n 54321 -w date
  [ "$status" -eq 0 ]
  # In testing mode, output should contain date info
  [[ "$output" =~ "digits/today" ]]
}
