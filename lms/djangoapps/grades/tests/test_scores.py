"""
Tests for grades.scores module.
"""
import os
import itertools
# pylint: disable=protected-access
from collections import namedtuple

import ddt
from django.test import TestCase
from django.utils.timezone import now
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator

import lms.djangoapps.grades.scores as scores
from lms.djangoapps.grades.models import BlockRecord
from lms.djangoapps.grades.transformer import GradesTransformer
from openedx.core.djangoapps.content.block_structure.block_structure import BlockData
from xmodule.graders import ProblemScore
from unittest import skipIf

NOW = now()


def submission_value_repr(self):
    """
    String representation for the SubmissionValue namedtuple which excludes
    the "created_at" attribute that changes with each execution.  Needed for
    consistency of ddt-generated test methods across pytest-xdist workers.
    """
    return '<SubmissionValue exists={}>'.format(self.exists)


def csm_value_repr(self):
    """
    String representation for the CSMValue namedtuple which excludes
    the "created" attribute that changes with each execution.  Needed for
    consistency of ddt-generated test methods across pytest-xdist workers.
    """
    return '<CSMValue exists={} raw_earned={}>'.format(self.exists, self.raw_earned)


def expected_result_repr(self):
    """
    String representation for the ExpectedResult namedtuple which excludes
    the "first_attempted" attribute that changes with each execution.  Needed
    for consistency of ddt-generated test methods across pytest-xdist workers.
    """
    included = ('raw_earned', 'raw_possible', 'weighted_earned', 'weighted_possible', 'weight', 'graded')
    attributes = ['{}={}'.format(name, getattr(self, name)) for name in included]
    return '<ExpectedResult {}>'.format(' '.join(attributes))


class TestScoredBlockTypes(TestCase):
    """
    Tests for the possibly_scored function.
    """
    shard = 4
    possibly_scored_block_types = {
        'course', 'chapter', 'sequential', 'vertical',
        'library_content', 'split_test', 'conditional', 'library', 'randomize',
        'problem', 'drag-and-drop-v2', 'openassessment', 'lti', 'lti_consumer',
        'videosequence', 'problemset', 'acid_parent', 'done', 'wrapper', 'edx_sga',
    }

    @skipIf(os.environ.get("CIRCLECI") == 'true', "Skip this test in CIRCLE CI.")
    def test_block_types_possibly_scored(self):
        self.assertTrue(self.possibly_scored_block_types.issubset(scores._block_types_possibly_scored()))

    def test_possibly_scored(self):
        course_key = CourseLocator(u'org', u'course', u'run')
        for block_type in self.possibly_scored_block_types:
            usage_key = BlockUsageLocator(course_key, block_type, 'mock_block_id')
            self.assertTrue(scores.possibly_scored(usage_key))


@ddt.ddt
class TestGetScore(TestCase):
    """
    Tests for get_score
    """
    shard = 4
    display_name = 'test_name'
    location = 'test_location'

    SubmissionValue = namedtuple('SubmissionValue', 'exists, points_earned, points_possible, created_at')
    SubmissionValue.__repr__ = submission_value_repr
    CSMValue = namedtuple('CSMValue', 'exists, raw_earned, raw_possible, created')
    CSMValue.__repr__ = csm_value_repr
    PersistedBlockValue = namedtuple('PersistedBlockValue', 'exists, raw_possible, weight, graded')
    ContentBlockValue = namedtuple('ContentBlockValue', 'raw_possible, weight, explicit_graded')
    ExpectedResult = namedtuple(
        'ExpectedResult',
        'raw_earned, raw_possible, weighted_earned, weighted_possible, weight, graded, first_attempted'
    )
    ExpectedResult.__repr__ = expected_result_repr

    def _create_submissions_scores(self, submission_value):
        """
        Creates a stub result from the submissions API for the given values.
        """
        if submission_value.exists:
            return {self.location: submission_value._asdict()}
        else:
            return {}

    def _create_csm_scores(self, csm_value):
        """
        Creates a stub result from courseware student module for the given values.
        """
        if csm_value.exists:
            stub_csm_record = namedtuple('stub_csm_record', 'correct, total, created')
            return {
                self.location: stub_csm_record(
                    correct=csm_value.raw_earned,
                    total=csm_value.raw_possible,
                    created=csm_value.created
                )
            }
        else:
            return {}

    def _create_persisted_block(self, persisted_block_value):
        """
        Creates and returns a minimal BlockRecord object with the give values.
        """
        if persisted_block_value.exists:
            return BlockRecord(
                self.location,
                persisted_block_value.weight,
                persisted_block_value.raw_possible,
                persisted_block_value.graded,
            )
        else:
            return None

    def _create_block(self, content_block_value):
        """
        Creates and returns a minimal BlockData object with the give values.
        """
        block = BlockData(self.location)
        block.display_name = self.display_name
        block.weight = content_block_value.weight

        block_grades_transformer_data = block.transformer_data.get_or_create(GradesTransformer)
        block_grades_transformer_data.max_score = content_block_value.raw_possible
        setattr(
            block_grades_transformer_data,
            GradesTransformer.EXPLICIT_GRADED_FIELD_NAME,
            content_block_value.explicit_graded,
        )
        return block

    @ddt.data(
        # The value from Submissions trumps other values; The persisted value
        # from persisted-block trumps latest content values
        (
            SubmissionValue(exists=True, points_earned=50, points_possible=100, created_at=NOW),
            CSMValue(exists=True, raw_earned=10, raw_possible=40, created=NOW),
            PersistedBlockValue(exists=True, raw_possible=5, weight=40, graded=True),
            ContentBlockValue(raw_possible=1, weight=20, explicit_graded=False),
            ExpectedResult(
                raw_earned=None, raw_possible=None,
                weighted_earned=50, weighted_possible=100,
                weight=40, graded=True, first_attempted=NOW
            ),
        ),
        # same as above, except Submissions doesn't exist; CSM values used
        (
            SubmissionValue(exists=False, points_earned=50, points_possible=100, created_at=NOW),
            CSMValue(exists=True, raw_earned=10, raw_possible=40, created=NOW),
            PersistedBlockValue(exists=True, raw_possible=5, weight=40, graded=True),
            ContentBlockValue(raw_possible=1, weight=20, explicit_graded=False),
            ExpectedResult(
                raw_earned=10, raw_possible=40,
                weighted_earned=10, weighted_possible=40,
                weight=40, graded=True, first_attempted=NOW,
            ),
        ),
        # CSM values exist, but with NULL earned score treated as not-attempted
        (
            SubmissionValue(exists=False, points_earned=50, points_possible=100, created_at=NOW),
            CSMValue(exists=True, raw_earned=None, raw_possible=40, created=NOW),
            PersistedBlockValue(exists=True, raw_possible=5, weight=40, graded=True),
            ContentBlockValue(raw_possible=1, weight=20, explicit_graded=False),
            ExpectedResult(
                raw_earned=0, raw_possible=40,
                weighted_earned=0, weighted_possible=40,
                weight=40, graded=True, first_attempted=None
            ),
        ),
        # neither submissions nor CSM exist; Persisted values used
        (
            SubmissionValue(exists=False, points_earned=50, points_possible=100, created_at=NOW),
            CSMValue(exists=False, raw_earned=10, raw_possible=40, created=NOW),
            PersistedBlockValue(exists=True, raw_possible=5, weight=40, graded=True),
            ContentBlockValue(raw_possible=1, weight=20, explicit_graded=False),
            ExpectedResult(
                raw_earned=0, raw_possible=5,
                weighted_earned=0, weighted_possible=40,
                weight=40, graded=True, first_attempted=None
            ),
        ),
        # none of submissions, CSM, or persisted exist; Latest content values used
        (
            SubmissionValue(exists=False, points_earned=50, points_possible=100, created_at=NOW),
            CSMValue(exists=False, raw_earned=10, raw_possible=40, created=NOW),
            PersistedBlockValue(exists=False, raw_possible=5, weight=40, graded=True),
            ContentBlockValue(raw_possible=1, weight=20, explicit_graded=False),
            ExpectedResult(
                raw_earned=0, raw_possible=1,
                weighted_earned=0, weighted_possible=20,
                weight=20, graded=False,
                first_attempted=None
            ),
        ),
    )
    @ddt.unpack
    def test_get_score(self, submission_value, csm_value, persisted_block_value, block_value, expected_result):
        score = scores.get_score(
            self._create_submissions_scores(submission_value),
            self._create_csm_scores(csm_value),
            self._create_persisted_block(persisted_block_value),
            self._create_block(block_value),
        )
        expected_score = ProblemScore(**expected_result._asdict())
        self.assertEquals(score, expected_score)


@ddt.ddt
class TestWeightedScore(TestCase):
    """
    Tests the helper method: weighted_score
    """
    shard = 4

    @ddt.data(
        (0, 0, 1),
        (5, 0, 0),
        (10, 0, None),
        (0, 5, None),
        (5, 10, None),
        (10, 10, None),
    )
    @ddt.unpack
    def test_cannot_compute(self, raw_earned, raw_possible, weight):
        self.assertEquals(
            scores.weighted_score(raw_earned, raw_possible, weight),
            (raw_earned, raw_possible),
        )

    @ddt.data(
        (0, 5, 0, (0, 0)),
        (5, 5, 0, (0, 0)),
        (2, 5, 1, (.4, 1)),
        (5, 5, 1, (1, 1)),
        (5, 5, 3, (3, 3)),
        (2, 4, 6, (3, 6)),
    )
    @ddt.unpack
    def test_computed(self, raw_earned, raw_possible, weight, expected_score):
        self.assertEquals(
            scores.weighted_score(raw_earned, raw_possible, weight),
            expected_score,
        )

    def test_assert_on_invalid_r_possible(self):
        with self.assertRaises(AssertionError):
            scores.weighted_score(raw_earned=1, raw_possible=None, weight=1)


@ddt.ddt
class TestInternalGetGraded(TestCase):
    """
    Tests the internal helper method: _get_explicit_graded
    """
    shard = 4

    def _create_block(self, explicit_graded_value):
        """
        Creates and returns a minimal BlockData object with the give value
        for explicit_graded.
        """
        block = BlockData('any_key')
        setattr(
            block.transformer_data.get_or_create(GradesTransformer),
            GradesTransformer.EXPLICIT_GRADED_FIELD_NAME,
            explicit_graded_value,
        )
        return block

    @ddt.data(None, True, False)
    def test_with_no_persisted_block(self, explicitly_graded_value):
        block = self._create_block(explicitly_graded_value)
        self.assertEquals(
            scores._get_graded_from_block(None, block),
            explicitly_graded_value is not False,  # defaults to True unless explicitly False
        )

    @ddt.data(
        *itertools.product((True, False), (True, False, None))
    )
    @ddt.unpack
    def test_with_persisted_block(self, persisted_block_value, block_value):
        block = self._create_block(block_value)
        block_record = BlockRecord(block.location, 0, 0, persisted_block_value)
        self.assertEquals(
            scores._get_graded_from_block(block_record, block),
            block_record.graded,  # persisted value takes precedence
        )


@ddt.ddt
class TestInternalGetScoreFromBlock(TestCase):
    """
    Tests the internal helper method: _get_score_from_persisted_or_latest_block
    """
    shard = 4

    def _create_block(self, raw_possible):
        """
        Creates and returns a minimal BlockData object with the give value
        for raw_possible.
        """
        block = BlockData('any_key')
        block.transformer_data.get_or_create(GradesTransformer).max_score = raw_possible
        return block

    def _verify_score_result(self, persisted_block, block, weight, expected_r_possible):
        """
        Verifies the result of _get_score_from_persisted_or_latest_block is as expected.
        """
        # pylint: disable=unbalanced-tuple-unpacking
        (
            raw_earned, raw_possible, weighted_earned, weighted_possible, first_attempted
        ) = scores._get_score_from_persisted_or_latest_block(persisted_block, block, weight)

        self.assertEquals(raw_earned, 0.0)
        self.assertEquals(raw_possible, expected_r_possible)
        self.assertEquals(weighted_earned, 0.0)
        if weight is None or expected_r_possible == 0:
            self.assertEquals(weighted_possible, expected_r_possible)
        else:
            self.assertEquals(weighted_possible, weight)
        self.assertIsNone(first_attempted)

    @ddt.data(
        *itertools.product((0, 1, 5), (None, 0, 1, 5))
    )
    @ddt.unpack
    def test_with_no_persisted_block(self, block_r_possible, weight):
        block = self._create_block(block_r_possible)
        self._verify_score_result(None, block, weight, block_r_possible)

    @ddt.data(
        *itertools.product((0, 1, 5), (None, 0, 1, 5), (None, 0, 1, 5))
    )
    @ddt.unpack
    def test_with_persisted_block(self, persisted_block_r_possible, block_r_possible, weight):
        block = self._create_block(block_r_possible)
        block_record = BlockRecord(block.location, 0, persisted_block_r_possible, False)
        self._verify_score_result(block_record, block, weight, persisted_block_r_possible)
