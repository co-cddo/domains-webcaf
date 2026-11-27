from concurrent.futures import ThreadPoolExecutor
from threading import Event

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.db import connection, connections, transaction
from django.forms.models import inlineformset_factory
from django.test import RequestFactory, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from webcaf.webcaf.admin import (
    AllowedEmailDomainAdmin,
    OrganisationAdmin,
    OrganisationEmailDomainAdmin,
    OrganisationEmailDomainAdminForm,
    OrganisationEmailDomainInline,
    OrganisationEmailDomainInlineFormSet,
)
from webcaf.webcaf.models import AllowedEmailDomain, Organisation, OrganisationEmailDomain


class OrganisationEmailDomainInlineTest(TestCase):
    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Council",
            organisation_type="council",
            gss_code="E06000001",
        )
        self.first_domain = AllowedEmailDomain.objects.create(domain="first.gov.uk")
        self.second_domain = AllowedEmailDomain.objects.create(domain="second.gov.uk")
        self.formset_class = inlineformset_factory(
            Organisation,
            OrganisationEmailDomain,
            form=OrganisationEmailDomainAdminForm,
            formset=OrganisationEmailDomainInlineFormSet,
            fields=["domain", "is_primary", "status"],
            extra=0,
            can_delete=True,
        )

    def formset_data(self, links):
        data = {
            "domains-TOTAL_FORMS": str(len(links)),
            "domains-INITIAL_FORMS": str(sum(link.pk is not None for link in links)),
            "domains-MIN_NUM_FORMS": "0",
            "domains-MAX_NUM_FORMS": "1000",
        }
        for index, link in enumerate(links):
            data[f"domains-{index}-id"] = str(link.pk or "")
            data[f"domains-{index}-organisation"] = str(self.organisation.pk)
            data[f"domains-{index}-domain"] = str(link.domain_id)
            data[f"domains-{index}-status"] = link.status
            if link.is_primary:
                data[f"domains-{index}-is_primary"] = "on"
        return data

    def test_organisation_admin_contains_domain_inline(self):
        model_admin = OrganisationAdmin(Organisation, AdminSite())

        self.assertIn(OrganisationEmailDomainInline, model_admin.inlines)

    def test_rejects_two_primary_domains_with_clear_error(self):
        first_link = OrganisationEmailDomain(
            organisation=self.organisation,
            domain=self.first_domain,
            is_primary=True,
        )
        second_link = OrganisationEmailDomain(
            organisation=self.organisation,
            domain=self.second_domain,
            is_primary=True,
        )
        formset = self.formset_class(
            data=self.formset_data([first_link, second_link]),
            instance=self.organisation,
            prefix="domains",
            can_change_existing_links=True,
        )

        self.assertFalse(formset.is_valid())
        self.assertIn("at most one primary email domain", str(formset.non_form_errors()))

    def test_switches_primary_domain_in_one_submission(self):
        first_link = OrganisationEmailDomain.objects.create(
            organisation=self.organisation,
            domain=self.first_domain,
            is_primary=True,
        )
        second_link = OrganisationEmailDomain.objects.create(
            organisation=self.organisation,
            domain=self.second_domain,
        )
        first_link.is_primary = False
        second_link.is_primary = True
        formset = self.formset_class(
            data=self.formset_data([first_link, second_link]),
            instance=self.organisation,
            prefix="domains",
            can_change_existing_links=True,
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()

        first_link.refresh_from_db()
        second_link.refresh_from_db()
        self.assertFalse(first_link.is_primary)
        self.assertTrue(second_link.is_primary)
        # The explicit pre-save demotion and the submitted form save are both
        # audited. Complete history is more important than deduplicating these
        # two records.
        self.assertEqual(first_link.history.count(), 3)
        self.assertFalse(first_link.history.latest().is_primary)

    def test_switch_records_history_when_existing_primary_is_not_in_submitted_forms(self):
        first_link = OrganisationEmailDomain.objects.create(
            organisation=self.organisation,
            domain=self.first_domain,
            is_primary=True,
        )
        second_link = OrganisationEmailDomain(
            organisation=self.organisation,
            domain=self.second_domain,
            is_primary=True,
        )
        formset = self.formset_class(
            data=self.formset_data([second_link]),
            instance=self.organisation,
            prefix="domains",
            queryset=OrganisationEmailDomain.objects.none(),
            can_change_existing_links=True,
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()

        first_link.refresh_from_db()
        self.assertFalse(first_link.is_primary)
        self.assertFalse(first_link.history.latest().is_primary)


class OrganisationEmailDomainAdminTest(TestCase):
    def test_saving_primary_demotes_existing_primary_and_records_history(self):
        organisation = Organisation.objects.create(
            name="Test Council",
            organisation_type="council",
            gss_code="E06000001",
        )
        first_domain = AllowedEmailDomain.objects.create(domain="first.gov.uk")
        second_domain = AllowedEmailDomain.objects.create(domain="second.gov.uk")
        existing_primary = OrganisationEmailDomain.objects.create(
            organisation=organisation,
            domain=first_domain,
            is_primary=True,
        )
        new_primary = OrganisationEmailDomain(
            organisation=organisation,
            domain=second_domain,
            is_primary=True,
        )
        model_admin = OrganisationEmailDomainAdmin(OrganisationEmailDomain, AdminSite())
        request = RequestFactory().post("/admin/webcaf/organisationemaildomain/add/")
        request.user = User.objects.create_superuser(username="admin", email="admin@example.com")

        model_admin.save_model(request, new_primary, form=None, change=False)

        existing_primary.refresh_from_db()
        self.assertFalse(existing_primary.is_primary)
        self.assertFalse(existing_primary.history.latest().is_primary)


class OrganisationEmailDomainAdminHistoryTest(TestCase):
    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Council", organisation_type="council", gss_code="E06000001"
        )
        self.domain = AllowedEmailDomain.objects.create(domain="history.gov.uk")
        self.link = OrganisationEmailDomain.objects.create(organisation=self.organisation, domain=self.domain)
        self.link_id = self.link.pk
        self.organisation_id = self.organisation.pk
        self.domain_id = self.domain.pk
        self.client.force_login(User.objects.create_superuser(username="admin", email="admin@example.com"))

    def assert_history_is_readable(self, label):
        history = OrganisationEmailDomain.history.filter(id=self.link_id)
        self.assertEqual(history.count(), 2)
        response = self.client.get(reverse("admin:webcaf_organisationemaildomain_history", args=[self.link_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, label)
        for record in history:
            with self.subTest(history_id=record.history_id):
                self.assertEqual(str(record.instance), label)
                self.assertEqual(str(record.history_object), label)
                response = self.client.get(
                    reverse(
                        "admin:webcaf_organisationemaildomain_simple_history", args=[self.link_id, record.history_id]
                    )
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, label)

    def test_deleted_link_history_remains_readable_after_domain_deletion(self):
        self.link.delete()
        self.domain.delete()

        self.assert_history_is_readable(f"Test Council - Deleted domain (ID: {self.domain_id})")

    def test_deleted_link_history_remains_readable_after_organisation_deletion(self):
        self.link.delete()
        self.organisation.delete()

        self.assert_history_is_readable(f"Deleted organisation (ID: {self.organisation_id}) - history.gov.uk")

    def test_deleted_link_history_remains_readable_after_both_parents_are_deleted(self):
        self.link.delete()
        self.domain.delete()
        self.organisation.delete()

        self.assert_history_is_readable(
            f"Deleted organisation (ID: {self.organisation_id}) - Deleted domain (ID: {self.domain_id})"
        )

    def test_link_history_remains_readable_after_cascading_organisation_deletion(self):
        self.organisation.delete()

        self.assert_history_is_readable(f"Deleted organisation (ID: {self.organisation_id}) - history.gov.uk")


class OrganisationEmailDomainAdminPermissionTest(TestCase):
    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Council",
            organisation_type="council",
            gss_code="E06000001",
        )
        self.first_domain = AllowedEmailDomain.objects.create(domain="first.gov.uk")
        self.second_domain = AllowedEmailDomain.objects.create(domain="second.gov.uk")
        self.existing_primary = OrganisationEmailDomain.objects.create(
            organisation=self.organisation,
            domain=self.first_domain,
            is_primary=True,
        )
        self.user = User.objects.create_user(
            username="link-manager",
            email="link-manager@example.com",
            is_staff=True,
        )
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="webcaf",
                codename__in=[
                    "change_organisation",
                    "add_organisationemaildomain",
                    "view_allowedemaildomain",
                ],
            )
        )
        self.client.force_login(self.user)

    def grant_link_change_permission(self):
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="webcaf",
                codename="change_organisationemaildomain",
            )
        )

    def standalone_add_data(self):
        return {
            "organisation": str(self.organisation.pk),
            "domain": str(self.second_domain.pk),
            "is_primary": "on",
            "status": OrganisationEmailDomain.Status.ACTIVE,
            "_save": "Save",
        }

    def organisation_change_data(self):
        return {
            "name": self.organisation.name,
            "gss_code": self.organisation.gss_code,
            "organisation_type": self.organisation.organisation_type,
            "email_domain_links-TOTAL_FORMS": "1",
            "email_domain_links-INITIAL_FORMS": "0",
            "email_domain_links-MIN_NUM_FORMS": "0",
            "email_domain_links-MAX_NUM_FORMS": "1000",
            "email_domain_links-0-domain": str(self.second_domain.pk),
            "email_domain_links-0-is_primary": "on",
            "email_domain_links-0-status": OrganisationEmailDomain.Status.ACTIVE,
            "_save": "Save",
        }

    def assert_primary_is_unchanged(self):
        self.existing_primary.refresh_from_db()
        self.assertTrue(self.existing_primary.is_primary)
        self.assertFalse(
            OrganisationEmailDomain.objects.filter(
                organisation=self.organisation,
                domain=self.second_domain,
            ).exists()
        )

    def test_standalone_add_cannot_demote_primary_without_change_permission(self):
        response = self.client.post(
            reverse("admin:webcaf_organisationemaildomain_add"),
            self.standalone_add_data(),
        )

        self.assertEqual(response.status_code, 403)
        self.assert_primary_is_unchanged()

    def test_standalone_add_can_demote_primary_with_change_permission(self):
        self.grant_link_change_permission()

        response = self.client.post(
            reverse("admin:webcaf_organisationemaildomain_add"),
            self.standalone_add_data(),
        )

        self.assertEqual(response.status_code, 302)
        self.existing_primary.refresh_from_db()
        self.assertFalse(self.existing_primary.is_primary)
        self.assertTrue(
            OrganisationEmailDomain.objects.filter(
                organisation=self.organisation,
                domain=self.second_domain,
                is_primary=True,
            ).exists()
        )

    def test_inline_add_cannot_demote_omitted_primary_without_change_permission(self):
        response = self.client.post(
            reverse("admin:webcaf_organisation_change", args=[self.organisation.pk]),
            self.organisation_change_data(),
        )

        self.assertEqual(response.status_code, 403)
        self.assert_primary_is_unchanged()

    def test_inline_add_can_demote_primary_with_change_permission(self):
        self.grant_link_change_permission()

        response = self.client.post(
            reverse("admin:webcaf_organisation_change", args=[self.organisation.pk]),
            self.organisation_change_data(),
        )

        self.assertEqual(response.status_code, 302)
        self.existing_primary.refresh_from_db()
        self.assertFalse(self.existing_primary.is_primary)
        self.assertTrue(
            OrganisationEmailDomain.objects.filter(
                organisation=self.organisation,
                domain=self.second_domain,
                is_primary=True,
            ).exists()
        )

    def test_link_only_staff_can_link_existing_domain_but_cannot_create_global_domain(self):
        response = self.client.get(reverse("admin:webcaf_organisation_change", args=[self.organisation.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="add_id_email_domain_links-__prefix__-domain"')
        self.assertFalse(
            response.context["inline_admin_formsets"][0].formset.empty_form.fields["domain"].widget.can_add_related
        )

        popup_url = reverse("admin:webcaf_allowedemaildomain_add")
        response = self.client.get(popup_url, {"_popup": "1", "_to_field": "id"})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            popup_url,
            {"domain": "new.gov.uk", "_popup": "1", "_to_field": "id", "_save": "Save"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AllowedEmailDomain.objects.filter(domain="new.gov.uk").exists())

        data = self.organisation_change_data()
        data.pop("email_domain_links-0-is_primary")
        response = self.client.post(
            reverse("admin:webcaf_organisation_change", args=[self.organisation.pk]),
            data,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AllowedEmailDomain.objects.count(), 2)
        self.assertTrue(
            OrganisationEmailDomain.objects.filter(
                organisation=self.organisation, domain=self.second_domain, is_primary=False
            ).exists()
        )
        self.existing_primary.refresh_from_db()
        self.assertTrue(self.existing_primary.is_primary)

    def test_authorised_staff_can_create_domain_from_council_page_and_link_it(self):
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="webcaf", codename="add_allowedemaildomain")
        )
        council_url = reverse("admin:webcaf_organisation_change", args=[self.organisation.pk])
        response = self.client.get(council_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="add_id_email_domain_links-__prefix__-domain"')
        widget = response.context["inline_admin_formsets"][0].formset.empty_form.fields["domain"].widget
        self.assertTrue(widget.can_add_related)
        popup_url = widget.get_context("email_domain_links-__prefix__-domain", None, {})["add_related_url"]
        response = self.client.get(popup_url, {"_popup": "1", "_to_field": "id"})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            popup_url,
            {"domain": "New.Gov.UK", "_popup": "1", "_to_field": "id", "_save": "Save"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/popup_response.html")
        domain = AllowedEmailDomain.objects.get(domain="new.gov.uk")
        self.assertJSONEqual(response.context["popup_response_data"], {"value": str(domain.pk), "obj": domain.domain})
        self.assertFalse(domain.organisation_links.exists())

        data = self.organisation_change_data()
        data["email_domain_links-0-domain"] = str(domain.pk)
        data.pop("email_domain_links-0-is_primary")
        response = self.client.post(council_url, data)

        self.assertEqual(response.status_code, 302)
        link = OrganisationEmailDomain.objects.get(organisation=self.organisation, domain=domain)
        self.assertEqual(domain.history.count(), 1)
        self.assertEqual(link.history.count(), 1)
        self.assertFalse(link.is_primary)


class AllowedEmailDomainAdminPermissionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = AllowedEmailDomainAdmin(AllowedEmailDomain, AdminSite())
        self.user = User.objects.create_user(
            username="domain-manager",
            email="domain-manager@example.com",
            is_staff=True,
        )
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="webcaf",
                codename__in=[
                    "add_organisationemaildomain",
                    "change_organisationemaildomain",
                    "delete_organisationemaildomain",
                    "view_allowedemaildomain",
                ],
            )
        )
        self.client.force_login(self.user)

    def request_for(self, user):
        request = self.factory.get("/admin/webcaf/allowedemaildomain/")
        request.user = user
        return request

    def test_association_permissions_do_not_authorise_global_allowlist_changes(self):
        request = self.request_for(self.user)

        self.assertFalse(self.model_admin.has_add_permission(request))
        self.assertFalse(self.model_admin.has_change_permission(request))
        self.assertFalse(self.model_admin.has_delete_permission(request))

    def test_global_allowlist_permission_explicitly_authorises_addition(self):
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="webcaf", codename="add_allowedemaildomain")
        )
        refreshed_user = User.objects.get(pk=self.user.pk)

        self.assertTrue(self.model_admin.has_add_permission(self.request_for(refreshed_user)))

    def test_admin_add_endpoint_rejects_user_without_global_allowlist_permission(self):
        response = self.client.post(
            reverse("admin:webcaf_allowedemaildomain_add"),
            {"domain": "new.gov.uk", "_save": "Save"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(AllowedEmailDomain.objects.filter(domain="new.gov.uk").exists())

    def test_admin_add_endpoint_allows_user_with_global_allowlist_permission(self):
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="webcaf", codename="add_allowedemaildomain")
        )

        response = self.client.post(
            reverse("admin:webcaf_allowedemaildomain_add"),
            {"domain": "new.gov.uk", "_save": "Save"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AllowedEmailDomain.objects.filter(domain="new.gov.uk").exists())

    def test_global_allowlist_permissions_explicitly_authorise_changes_and_deletion(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="webcaf",
                codename__in=["change_allowedemaildomain", "delete_allowedemaildomain"],
            )
        )
        refreshed_user = User.objects.get(pk=self.user.pk)
        request = self.request_for(refreshed_user)

        self.assertTrue(self.model_admin.has_change_permission(request))
        self.assertTrue(self.model_admin.has_delete_permission(request))

    def test_admin_add_endpoint_does_not_create_mixed_case_duplicate(self):
        AllowedEmailDomain.objects.create(domain="kent.gov.uk")
        superuser = User.objects.create_superuser(username="admin", email="admin@example.com")
        self.client.force_login(superuser)

        response = self.client.post(
            reverse("admin:webcaf_allowedemaildomain_add"),
            {"domain": "Kent.Gov.UK", "_save": "Save"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AllowedEmailDomain.objects.filter(domain="kent.gov.uk").count(), 1)


class AllowedEmailDomainAdminDeletionTest(TestCase):
    def setUp(self):
        self.domain = AllowedEmailDomain.objects.create(domain="shared.gov.uk")
        self.unlinked_domain = AllowedEmailDomain.objects.create(domain="unlinked.gov.uk")
        self.links = []
        for name, gss_code in [("First Council", "E06000001"), ("Second Council", "E06000002")]:
            organisation = Organisation.objects.create(name=name, organisation_type="council", gss_code=gss_code)
            self.links.append(
                OrganisationEmailDomain.objects.create(organisation=organisation, domain=self.domain, is_primary=True)
            )
        self.client.force_login(User.objects.create_superuser(username="admin", email="admin@example.com"))

    def assert_shared_domain_is_unchanged(self):
        self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.domain.pk).exists())
        self.assertEqual(self.domain.history.count(), 1)
        for link in self.links:
            link.refresh_from_db()
            self.assertTrue(link.is_primary)
            self.assertEqual(link.history.count(), 1)

    def test_delete_page_blocks_shared_domain_deletion_even_for_superuser(self):
        url = reverse("admin:webcaf_allowedemaildomain_delete", args=[self.domain.pk])
        for method in ["get", "post"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, {"post": "yes"} if method == "post" else {})

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["protected"])
                self.assertContains(response, "First Council")
                self.assertContains(response, "Second Council")
                self.assert_shared_domain_is_unchanged()

    def test_bulk_delete_blocks_entire_selection_if_a_domain_is_linked(self):
        url = reverse("admin:webcaf_allowedemaildomain_changelist")
        data = {
            "action": "delete_selected",
            "_selected_action": [str(self.domain.pk), str(self.unlinked_domain.pk)],
        }
        for confirmed in [False, True]:
            with self.subTest(confirmed=confirmed):
                if confirmed:
                    data["post"] = "yes"
                response = self.client.post(url, data)

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["protected"])
                self.assert_shared_domain_is_unchanged()
                self.assertTrue(AllowedEmailDomain.objects.filter(pk=self.unlinked_domain.pk).exists())

    def test_unlinked_domain_can_be_deleted_by_authorised_staff(self):
        response = self.client.post(
            reverse("admin:webcaf_allowedemaildomain_delete", args=[self.unlinked_domain.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AllowedEmailDomain.objects.filter(pk=self.unlinked_domain.pk).exists())
        self.assert_shared_domain_is_unchanged()

    def test_unlinked_domain_can_be_bulk_deleted_by_authorised_staff(self):
        response = self.client.post(
            reverse("admin:webcaf_allowedemaildomain_changelist"),
            {"action": "delete_selected", "_selected_action": [str(self.unlinked_domain.pk)], "post": "yes"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AllowedEmailDomain.objects.filter(pk=self.unlinked_domain.pk).exists())
        self.assert_shared_domain_is_unchanged()


@skipUnlessDBFeature("has_select_for_update")
class OrganisationEmailDomainAdminConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Council", organisation_type="council", gss_code="E06000001"
        )
        self.domains = [
            AllowedEmailDomain.objects.create(domain="first.gov.uk"),
            AllowedEmailDomain.objects.create(domain="second.gov.uk"),
        ]
        self.user = User.objects.create_superuser(username="admin", email="admin@example.com")

    def save_primary(self, path, domain, lock_attempted):
        def track_organisation_lock(execute, sql, params, many, context):
            if "FOR UPDATE" in sql and f'"{Organisation._meta.db_table}"' in sql:
                lock_attempted.set()
            return execute(sql, params, many, context)

        try:
            # Bound failures so a broken lock cannot leave a test worker stuck.
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '15s'")
            with connection.execute_wrapper(track_organisation_lock):
                if path == "standalone":
                    model_admin = OrganisationEmailDomainAdmin(OrganisationEmailDomain, AdminSite())
                    request = RequestFactory().post("/admin/webcaf/organisationemaildomain/add/")
                    request.user = self.user
                    model_admin.save_model(
                        request,
                        OrganisationEmailDomain(organisation=self.organisation, domain=domain, is_primary=True),
                        form=None,
                        change=False,
                    )
                else:
                    formset_class = inlineformset_factory(
                        Organisation,
                        OrganisationEmailDomain,
                        form=OrganisationEmailDomainAdminForm,
                        formset=OrganisationEmailDomainInlineFormSet,
                        fields=["domain", "is_primary", "status"],
                        extra=0,
                    )
                    formset = formset_class(
                        instance=self.organisation,
                        prefix="domains",
                        data={
                            "domains-TOTAL_FORMS": "1",
                            "domains-INITIAL_FORMS": "0",
                            "domains-MIN_NUM_FORMS": "0",
                            "domains-MAX_NUM_FORMS": "1000",
                            "domains-0-domain": str(domain.pk),
                            "domains-0-is_primary": "on",
                            "domains-0-status": OrganisationEmailDomain.Status.ACTIVE,
                        },
                        can_change_existing_links=True,
                    )
                    self.assertTrue(formset.is_valid(), formset.errors)
                    formset.save()
        finally:
            connections.close_all()

    def assert_concurrent_primary_assignments(self, paths):
        lock_attempts = [Event(), Event()]
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Both requests start with no primary and must wait for this same
            # parent-row lock before looking up the current primary.
            with transaction.atomic():
                Organisation.objects.select_for_update().get(pk=self.organisation.pk)
                futures = [
                    executor.submit(self.save_primary, path, domain, attempted)
                    for path, domain, attempted in zip(paths, self.domains, lock_attempts)
                ]
                attempted_locks = [attempted.wait(timeout=5) for attempted in lock_attempts]
            for future in futures:
                future.result(timeout=20)

        self.assertEqual(attempted_locks, [True, True])
        links = OrganisationEmailDomain.objects.filter(organisation=self.organisation)
        self.assertEqual(links.count(), 2)
        self.assertEqual(links.filter(is_primary=True).count(), 1)
        demoted = links.get(is_primary=False)
        self.assertEqual(demoted.history.count(), 2)
        self.assertFalse(demoted.history.latest().is_primary)

    def test_concurrent_standalone_first_primary_assignments(self):
        self.assert_concurrent_primary_assignments(["standalone", "standalone"])

    def test_concurrent_inline_first_primary_assignments(self):
        self.assert_concurrent_primary_assignments(["inline", "inline"])

    def test_concurrent_inline_and_standalone_first_primary_assignments(self):
        self.assert_concurrent_primary_assignments(["inline", "standalone"])
