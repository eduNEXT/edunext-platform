Open edX Filters
================

How to use
----------

Using openedx-filters in your code is very straight forward. We can consider the
two possible cases:

Configuring a filter
^^^^^^^^^^^^^^^^^^^^

Implement pipeline steps
************************

Let's say you want to consult student's information with a third party service
before generating the students certificate. This is a common use case for filters,
where the functions part of the filter's pipeline will perform the consulting tasks and
decide the execution flow for the application. These functions are the pipeline steps,
and can be implemented in an installable Python library:

.. code-block:: python

    # Step implementation taken from openedx-filters-samples plugin
    from openedx_filters import PipelineStep
    from openedx_filters.learning.filters import CertificateCreationRequested

    class StopCertificateCreation(PipelineStep):

        def run_filter(self, user, course_id, mode, status):
            # Consult third party service and check if continue
            raise CertificateCreationRequested.PreventCertificateCreation(
                "You can't generate a certificate from this site."
            )

There's two key components to the implementation:

1. The filter step must be a subclass of ``PipelineStep``.

2. The ``run_filter`` signature must match the filters definition, eg.,
the previous step matches the method's definition in CertificateCreationRequested.

Attach/hook pipeline to filter
******************************

After implementing the pipeline steps, we have to tell the certificate creation
filter to execute our pipeline.

.. code-block:: python

    OPEN_EDX_FILTERS_CONFIG = {
        "org.openedx.learning.certificate.creation.requested.v1": {
            "fail_silently": False,
            "pipeline": [
                "openedx_filters_samples.samples.pipeline.StopCertificateCreation"
            ]
        },
    }

Triggering a filter
^^^^^^^^^^^^^^^^^^^

In order to execute a filter in your own plugin/library, you must install the
library where the steps are implemented and also, ``openedx-filters``.

.. code-block:: python

    from openedx_filters.learning.filters import CertificateCreationRequested

    try:
        self.user, self.course_id, self.mode, self.status = CertificateCreationRequested.run_filter(
            user=self.user, course_id=self.course_id, mode=self.mode, status=self.status,
        )
    except CertificateCreationRequested.PreventCertificateCreation as exc:
        raise CertificateGenerationNotAllowed(str(exc)) from exc

Testing filters
^^^^^^^^^^^^^^^

The main limitation while testing filters it's their arguments, as they are edxapp memory
objects, but that can be solved in CI using mocks. To test your pipeline steps you need
to include the openedx-filters library in your testing dependencies and configure them
in your test case.

.. code-block:: python

   from openedx_filters.learning.filters import CertificateCreationRequested

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.openedx.learning.certificate.creation.requested.v1": {
                "fail_silently": False,
                "pipeline": [
                    "openedx_filters_samples.samples.pipeline.StopCertificateCreation"
                ]
            }
        }
    )
    def test_stop_certificate_creation(self):
        """
        Test that the certificate creation request stops.
        """
        with self.assertRaises(CertificateCreationRequested.PreventCertificateCreation):
            CertificateCreationRequested.run_filter(
                user=self.user, course_key=self.course_key, mode="audit",
            )

        # run your assertions

Changes in the openedx-filters library that are not compatible with your code
should break this kind of test in CI and let you know you need to upgrade your
code.

Live example
^^^^^^^^^^^^

For filter steps samples you can visit the `openedx-filters-samples`_ plugin, where
you can find minimal steps exemplifying the different ways on how to use
``openedx-filters``.

.. _openedx-filters-samples: https://github.com/eduNEXT/openedx-filters-samples


Index of Filters
-----------------

This list contains the filters currently being executed by edx-platform. The provided
links target both the definition of the filter in the openedx-filters library as
well as the trigger location in this same repository.


.. list-table::
   :widths: 35 50 20

   * - *Name*
     - *Type*
     - *Date added*

   * - `StudentRegistrationRequested <https://github.com/eduNEXT/openedx-filters/blob/main/openedx_filters/learning/filters.py#L9>`_
     - org.openedx.learning.student.registration.requested.v1
     - `2021-09-02 <https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/user_authn/views/register.py#L258>`__

   * - `StudentLoginRequested <https://github.com/eduNEXT/openedx-filters/blob/main/openedx_filters/learning/filters.py#L40>`_
     - org.openedx.learning.student.login.requested.v1
     - `2021-09-02 <https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/user_authn/views/login.py#L306>`__

   * - `CourseEnrollmentStarted <https://github.com/eduNEXT/openedx-filters/blob/main/openedx_filters/learning/filters.py#L70>`_
     - org.openedx.learning.course.enrollment.started.v1
     - `2021-09-02 <https://github.com/edx/edx-platform/blob/master/common/djangoapps/student/models.py#L1675>`__

   * - `COURSE_ENROLLMENT_CHANGED <https://github.com/eduNEXT/openedx-events/blob/main/openedx_events/learning/signals.py#L54>`_
     - org.openedx.learning.course.enrollment.changed.v1
     - `2021-09-22 <https://github.com/edx/edx-platform/blob/master/common/djangoapps/student/models.py#L1675>`__

   * - `COURSE_UNENROLLMENT_COMPLETED <https://github.com/eduNEXT/openedx-events/blob/main/openedx_events/learning/signals.py#L66>`_
     - org.openedx.learning.course.unenrollment.completed.v1
     - `2021-09-22 <https://github.com/edx/edx-platform/blob/master/common/djangoapps/student/models.py#L1468>`__

   * - `CERTIFICATE_CREATED <https://github.com/eduNEXT/openedx-events/blob/main/openedx_events/learning/signals.py#L78>`_
     - org.openedx.learning.certificate.created.v1
     - `2021-09-22 <https://github.com/edx/edx-platform/blob/master/lms/djangoapps/certificates/models.py#L506>`__

   * - `CERTIFICATE_CHANGED <https://github.com/eduNEXT/openedx-events/blob/main/openedx_events/learning/signals.py#L90>`_
     - org.openedx.learning.certificate.changed.v1
     - `2021-09-22 <https://github.com/edx/edx-platform/blob/master/lms/djangoapps/certificates/models.py#L475>`__

   * - `CERTIFICATE_REVOKED <https://github.com/eduNEXT/openedx-events/blob/main/openedx_events/learning/signals.py#L102>`_
     - org.openedx.learning.certificate.revoked.v1
     - `2021-09-22 <https://github.com/edx/edx-platform/blob/master/lms/djangoapps/certificates/models.py#L397>`__

   * - `COHORT_MEMBERSHIP_CHANGED <https://github.com/eduNEXT/openedx-events/blob/main/openedx_events/learning/signals.py#L114>`_
     - org.openedx.learning.cohort_membership.changed.v1
     - `2021-09-22 <https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/course_groups/models.py#L135>`__
