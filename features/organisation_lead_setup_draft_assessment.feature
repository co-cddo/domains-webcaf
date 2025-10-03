Feature: Organisation lead can edit an organisation's details

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "other@example.gov.uk" exists
    And User "other@example.gov.uk" has the profile "Organisation lead" assigned in "Ministry of Agriculture"
    And the application is running
    And the user logs in with username  "other@example.gov.uk" and password "password"
    And click button with text "Start a self-assessment"
    And click link with text "Provide system details"
    And select select box with value "System 2"
    And click button with text "Save and continue"
    And click link with text "Choose your government CAF profile"
    And select radio with value "baseline"
    And click button with text "Save and continue"
    And click link with text "Choose a review type"
    And select radio with value "peer_review"
    And click button with text "Save and continue"


  Scenario: Org lead setup a draft assessment with basic profile
    Given Think time 2 seconds
    And get assessment id from url and add to context
    Then confirm initial assessment has system "System 2" caf profile "baseline" and review type "peer_review"

  Scenario: Org lead setup a draft assessment with basic profile and then edit its values
    Given Think time 2 seconds
    And get assessment id from url and add to context
    And click link with text "Provide system details"
    And select select box with value "System 1"
    And click button with text "Save and continue"
    And click link with text "Choose your government CAF profile"
    And select radio with value "enhanced"
    And click button with text "Save and continue"
    And page has heading "You have chosen an enhanced CAF profile for this system"
    And click button with text "Continue"
    And click link with text "Choose a review type"
    And page has heading "You have chosen an enhanced CAF profile for this system"
    And click button with text "Continue"
    Then confirm initial assessment has system "System 1" caf profile "enhanced" and review type "independent"
