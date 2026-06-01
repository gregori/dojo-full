# language: en
Feature: Student Check-in
  As a student
  I want to check in to a class or event
  So that my attendance is recorded and my progress is tracked

  Background:
    Given the database is empty
    And belt "6º Kyu" exists for category "adult" with sort order 1
    And event type "Aula Regular" exists with color "#3498db"
    And a student "João Silva" exists with:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 1234         |
      | category            | adult        |
      | belt_name           | 6º Kyu       |
    And an event "Aula de Aikido - 30/05" exists with type "Aula Regular"

  @critical @smoke
  Scenario: Successful check-in via tablet
    When the student checks in with:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 1234         |
      | check_in_method     | tablet       |
    Then the response status should be 200
    And the response should contain "status" with value "success"
    And the student attendance should be recorded for the event
    And the response should contain the student progress information

  @critical
  Scenario: Check-in fails with incorrect PIN
    When the student checks in with:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 9999         |
      | check_in_method     | tablet       |
    Then the response status should be 401
    And the response should contain "detail" with value "Invalid PIN"
    And no attendance should be recorded

  Scenario: Check-in fails with non-existent registration
    When the student checks in with:
      | field               | value        |
      | registration_number | 9999999      |
      | pin                 | 1234         |
      | check_in_method     | tablet       |
    Then the response status should be 404
    And the response should contain "detail" with value "Student not found"

  @critical
  Scenario: Check-in via QR code
    Given the event has a valid check-in token
    When the student checks in via QR code with:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 1234         |
      | check_in_token      | <token>      |
    Then the response status should be 200
    And the check-in method should be "qrcode"

  Scenario: Duplicate check-in prevention
    Given the student has already checked in to the event
    When the student checks in with:
      | field               | value        |
      | registration_number | 2024001      |
      | pin                 | 1234         |
      | check_in_method     | tablet       |
    Then the response status should be 400
    And the response should contain "detail" with value "Attendance already recorded"
