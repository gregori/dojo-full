# language: en
Feature: Notification Hub end-to-end trigger and history

  @smoke
  Scenario: A pre-check-in reminder fires once and appears in history
    Given an active student "Ana Silva" eligible for all events
    And an event "Aula de Aikido" starting in exactly 1 day
    When the daily notification check runs
    Then exactly one notification of type "pre_checkin_reminder" exists for the student
    When the student views their notification history with valid credentials
    Then the response includes a notification referencing "Aula de Aikido"

  Scenario: Running the check twice in the same day does not duplicate
    Given an active student "Ana Silva" eligible for all events
    And an event "Aula de Aikido" starting in exactly 1 day
    When the daily notification check runs twice
    Then exactly one notification of type "pre_checkin_reminder" exists for the student
