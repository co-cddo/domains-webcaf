Feature: Cyber advisor can maintain systems


  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
#    Database does not store the passwords
    And the user "cyber_advisor@example.gov.uk" exists
    And User "cyber_advisor@example.gov.uk" has the profile "GDS cyber advisor" assigned in "Ministry of Agriculture"
    And the application is running
    And the user logs in with username  "cyber_advisor@example.gov.uk" and password "password"
    And there is no system with name "My system" for organisation "Ministry of Agriculture"


  Scenario: GDS cyber advisor can see option to create systems
    Given Think time 2 seconds
    Then they should see page title "My account - cyber_advisor"
    And current organisation is set to "Ministry of Agriculture"
    And a button with text "Add new system"
    And link with text "View systems"
    And link with text "Manage users"
    When click link with text "View systems"
    Then they should see page title "Manage Systems - cyber_advisor"
    And link with text "System 1"
    And link with text "System 2"
    And link with text "System 3"

  Scenario: GDS cyber advisor can crete new System
    Given Think time 2 seconds
    Then they should see page title "My account - cyber_advisor"
    And current organisation is set to "Ministry of Agriculture"
    And a button with text "Add new system"
    And link with text "View systems"
    And link with text "Manage users"
    When click link with text "View systems"
    Then they should see page title "Manage Systems - cyber_advisor"
    And link with text "System 1"
    And link with text "System 2"
    And link with text "System 3"
    And click button with text "Continue"
    And enter text "My system" for id "id_name"
    And select radio with value "supports_other_critical_systems"
    And enter text "My description" for id "id_description"
    And select checkbox with value "owned_by_another_government_organisation"
    And select checkbox with value "hosted_hybrid"
    And select radio with value "yes"
    And select radio with value "assessed_in_2425"
    And click button with text "Save and continue"
    Then they should see page title "Check system details"
    Then they should see a summary card with header "Ministry of Agriculture" keys "System name, Essential services, System ownership,System type,Hosting and connectivity,Internet facing,GovAssure year" and values "My system, My description, Another government organisation,The system is a corporate or enterprise system or network that supports other critical systems,Hybrid,Yes,'Yes, assessed in 2024/25'"
    And click button with text "Save and continue"
#    User should see the new system in the system details page
    Then they should see page title "Manage Systems - cyber_advisor"
    And link with text "My system"
    And System "does" exist with name "My system" for organisation "Ministry of Agriculture"


  Scenario: GDS cyber advisor can update a System
    Given Think time 2 seconds
    Then they should see page title "My account - cyber_advisor"
    And current organisation is set to "Ministry of Agriculture"
    And a button with text "Add new system"
    And link with text "View systems"
    And link with text "Manage users"
    When click link with text "View systems"
    Then they should see page title "Manage Systems - cyber_advisor"
    And link with text "System 1"
    And link with text "System 2"
    And link with text "System 3"
    And click link with text "System 3"
    And enter text "My description - updated" for id "id_description"
    And select radio with value "supports_other_critical_systems"
    And select checkbox with value "owned_by_another_government_organisation"
    And select checkbox with value "hosted_hybrid"
    And select radio with value "yes"
    And select radio with value "assessed_in_2425"
    And click button with text "Save and continue"
    Then they should see page title "Check system details"
    Then they should see a summary card with header "Ministry of Agriculture" keys "System name, Essential services, System ownership,System type,Hosting and connectivity,Internet facing,GovAssure year" and values "System 3, My description - updated, Another government organisation,The system is a corporate or enterprise system or network that supports other critical systems,Hybrid,Yes,'Yes, assessed in 2024/25'"
    And click button with text "Save and continue"
#    User should see the new system in the system details page
    Then they should see page title "Manage Systems - cyber_advisor"
    And System "does" exist with name "System 3" for organisation "Ministry of Agriculture"
