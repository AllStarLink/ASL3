#!/usr/bin/env bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../bin/asl-node-lookup"

  # Inject mocks
  PATH="$BATS_TEST_DIRNAME/mocks:$PATH"
}

@test "fails if node not specified" {
  run "$SCRIPT"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "fails for non-numeric node" {
  run "$SCRIPT" abcd
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Node number not valid" ]]
}

@test "fails for node that is too short" {
  run "$SCRIPT" 123
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Node number not valid" ]]
}

@test "prints SRV, A, and TXT records for valid node" {
  run "$SCRIPT" 12345
  [ "$status" -eq 0 ]

  [[ "$output" =~ "SRV (_iax._udp.12345.nodes.allstarlink.org)" ]]
  [[ "$output" =~ "A (12345.nodes.allstarlink.org)" ]]
  [[ "$output" =~ "TXT (12345.nodes.allstarlink.org)" ]]
}

@test "prints 'No SRV record' when SRV lookup fails" {
  export MOCK_NO_SRV=1
  run "$SCRIPT" 12345
  unset MOCK_NO_SRV

  [ "$status" -eq 0 ]
  [[ "$output" =~ "No SRV record" ]]
}

@test "shows SOA and NS records in verbose mode" {
  run "$SCRIPT" --verbose 12345
  [ "$status" -eq 0 ]

  [[ "$output" =~ "SOA (nodes.allstarlink.org)" ]]
  [[ "$output" =~ "NS (nodes.allstarlink.org)" ]]
}

@test "prints asterisk message when not root or asterisk user" {
  run "$SCRIPT" 12345
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Use \"sudo" ]]
}

@test "--help prints usage and exits non-zero" {
  run "$SCRIPT" --help
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}
