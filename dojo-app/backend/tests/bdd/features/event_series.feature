# language: en
Feature: Recurring event series check-in

  Background:
    Given the database is empty
    And belt "6º Kyu" exists for category "adult" with sort order 1
    And event type "Aula Regular" exists with color "#3498db"
    And a student "João Silva" exists with:
      | field               | value        |
      | registration_number | 2024801      |
      | pin                 | 1234         |
      | category            | adult        |
      | belt_name           | 6º Kyu       |

  @critical @smoke
  Scenario: Scanning a series QR on a scheduled day checks in against today's occurrence
    Given a recurring event series "Aikido Geral" scheduled today at "07:00"
    When the student checks in via the series QR code with:
      | field               | value        |
      | registration_number | 2024801      |
      | pin                 | 1234         |
    Then the response status should be 200
    And exactly one event occurrence should exist for the series today

  @critical
  Scenario: Scanning a series QR twice in the same day resolves to the same occurrence
    Given a recurring event series "Aikido Geral" scheduled today at "07:00"
    And the series QR has already been scanned once today by another student
    When the student checks in via the series QR code with:
      | field               | value        |
      | registration_number | 2024801      |
      | pin                 | 1234         |
    Then the response status should be 200
    And exactly one event occurrence should exist for the series today

  Scenario: Scanning a series QR on a non-scheduled day is rejected
    Given a recurring event series "Aikido Geral" not scheduled today
    When the student checks in via the series QR code with:
      | field               | value        |
      | registration_number | 2024801      |
      | pin                 | 1234         |
    Then the response status should be 400
    And the response should contain "detail" with value "No occurrence scheduled today for this series"

  Scenario: A cancelled occurrence blocks check-in even via the series QR
    Given a recurring event series "Aikido Geral" scheduled today at "07:00"
    And today's occurrence for the series has been cancelled
    When the student checks in via the series QR code with:
      | field               | value        |
      | registration_number | 2024801      |
      | pin                 | 1234         |
    Then the response status should be 400
    And the response should contain "detail" with value "Event is cancelled"
