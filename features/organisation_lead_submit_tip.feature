Feature: GovAssure lead submits a TIP for independent assurance review

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
    And the user "alice@example.gov.uk" exists
    And User "alice@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the user "assessor_1@example.com" exists
    And User "assessor_1@example.com" has the profile "Independent assurance reviewer" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    And there is a "enhanced" profile assessment for "System 1", "Ministry of Agriculture", for the period "current" in "draft" status and data "alice_completed_assessment.json"

    Then the user logs in with username "alice@example.gov.uk" and password "password"
    And click link with text "View 1 draft self-assessment"
    And click link in table row containing value "System 1" with text "View"
    Then page has heading "Complete a WebCAF self-assessment"
    And get assessment id from url and add to context
    And confirm the current assessment has expected data "alice_completed_assessment.json"
    And confirm the current assessment has version as "caf40" type as "independent" and profile as "enhanced"
    And click link with text "Complete the full self-assessment"
    When click button with text "Save and Send for Review"
    Then page has heading "Self-assessment completed"
    # Prepopulate the review for the current assessment
    And there is a review assigned to the current assessment with the data "assessor_1_review.json" and status "in_progress"
    And logs out by clicking link
    # Simulate the assessor reviewing the assessment and submitting their review
    Given the application is running
    Then the user logs in with username "assessor_1@example.com" and password "password"
    And page has heading "Ministry of Agriculture self-assessments"
    And click link in table row containing value "System 1" with text "Review"
    And click link with text "Confirm system overview"
    And click button with text "Save and continue"
    And Enter IAR period
    And Add company details
    And Add review method
    And Add quality of self assessment
    Then click link with text "Create report"
    Then click button with text "Save and continue"
    Then click button with text "View report"
    Then page has heading "GovAssure Independent Assurance Review Report (IARR)"
    And page contains text "This report is UK OFFICIAL-SENSITIVE." in banner
    Then Navigate to review history page
    And page has heading "Report history"
    And click link with text "Mark latest report version as final"
    Then page has heading "Do you want version 1 to be the final report?"
    And click button with text "Confirm and make final"
    #    Tip is automatically created after marking the report as final
    Then the user should be able to download the "pdf" report "/review/<review_id>/1/download-report/" and save as "review_report"
    Then the user should be able to download the "xlsx" report "/review/<review_id>/1/download-excel-report/" and save as "review_excel_data"
    And logs out by clicking link

  Scenario: GovAssure lead submits a TIP for independent assurance review
    Given the application is running
    When the user logs in with username "alice@example.gov.uk" and password "password"
#    Tip will be automatically created once the assessor has finalised the report
    And click link with text "View and manage your 1 TIP"
    And click link with text "Start TIP"
    Then page has heading "Create a Targeted Improvement Plan (TIP)"
    And store current tip id from the url
    And click link with text "Priority recommendations (1)"
    And click link with text "Add response"
    Then page has subheading "Contributing outcome: D2.b Using Incidents to Drive Improvements"
    And select radio "actioned_answer_yes"
    And enter text "My action text" for id "action_taken_description"
    And enter text "Uncle Bob" for id "action_owner"
    And select radio "resources_available"
    And select radio "budget_available"
    And select radio "target_date_not_provided"
    And enter text "Will do later" for id "target_date_unavailable_reason"
    Then click button with text "Save and return to summary"
    And click link with text "Return to task list"
    And click link with text "Other recommendations (1)"
    Then select radio "confirm_bulk_review"
    And click button with text "Save and continue"
    Then page contains text "All remaining other recommendations have been marked as reviewed with no action planned." in paragraph
    And click link with text "Return to task list"
    And click link with text "Review your actions and get a draft TIP"
    Then they should see a summary card with header "REC-D2B1 — D2.b Using Incidents to Drive Improvements" keys "Reviewer recommendation,Action,Action owner,Resource available,Budget approved,Reason no target date given" and values "REC-D2B1 - Recommendation for improvement D2.b,My action text,Uncle Bob,Yes,Yes,Will do later"
    And they should see a summary card with header " REC-A1A1 — A1.a Board Direction" keys "Reviewer recommendation,No action planned" and values "REC-A1A1 - Recommendation for improvement A1.a, Not provided"
    Then click button with text "Mark as complete"
    Then the user should be able to download the "pdf" report "/tip/<tip_id>/view-report?mode=pdf" and save as "tip_report"
    Then the user should be able to download the "xlsx" report "/tip/<tip_id>/view-report?mode=template" and save as "tip_template"
