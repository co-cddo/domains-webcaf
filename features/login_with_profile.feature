Feature: User login without a profile


  Background:
    Given Organisation Ministry of Agriculture of type ministerial-department exists with systems System 1, System 2, System 3
#    Database does not store the passwords
    And the user admin@example.gov.uk exists
    And User admin@example.gov.uk has the profile GovAssure Lead assigned in Ministry of Agriculture

  Scenario Outline: Valid user logs in <user_name>
    Given the application is running
    And Think time 5 seconds
    When the user logs in with username  <user_name> and password <password>
    Then they should see page title <page_title>
    And page contains text <page_text> in banner
    Examples:
      | user_name            | password | page_title         | page_text                                                                                                                                        |
      | admin@example.gov.uk | password | My account - admin | Before starting a new CAF self-assessment, you must have a completed and signed off scoping document for stage 1 and 2 of the GovAssure process. |
