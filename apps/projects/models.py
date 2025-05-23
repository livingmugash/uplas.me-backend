import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

# Choices for Project Difficulty
PROJECT_DIFFICULTY_CHOICES = [
    ('beginner', _('Beginner')),
    ('intermediate', _('Intermediate')),
    ('advanced', _('Advanced')),
    ('expert', _('Expert')),
]

# Choices for UserProject Status
USER_PROJECT_STATUS_CHOICES = [
    ('not_started', _('Not Started')), # User has access but hasn't begun
    ('in_progress', _('In Progress')),
    ('submitted', _('Submitted for Assessment')),
    ('assessed', _('Assessed')), # Assessment complete, see ProjectAssessment for pass/fail
    ('completed', _('Completed Successfully')), # Passed assessment
    ('failed', _('Failed Assessment')), # Did not pass assessment
    ('archived', _('Archived')), # User archived it
]

class ProjectTag(models.Model):
    """
    Tags for categorizing projects (e.g., Python, JavaScript, Machine Learning, Web App).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Tag Name'))
    slug = models.SlugField(max_length=60, unique=True, verbose_name=_('Slug'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Project Tag')
        verbose_name_plural = _('Project Tags')
        ordering = ['name']

    def __str__(self):
        return self.name

class Project(models.Model):
    """
    Defines a project template or a specific project challenge.
    This can be created by admins/instructors or generated by AI.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name=_('Project Title'))
    slug = models.SlugField(max_length=220, unique=True, verbose_name=_('Slug'))
    description = models.TextField(verbose_name=_('Project Description'))
    difficulty_level = models.CharField(
        max_length=20,
        choices=PROJECT_DIFFICULTY_CHOICES,
        default='intermediate',
        verbose_name=_('Difficulty Level')
    )
    estimated_duration_hours = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_('Estimated Duration (Hours)'),
        help_text=_("Estimated time a user might spend on this project.")
    )
    learning_outcomes = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Learning Outcomes'),
        help_text=_("List of skills or concepts the user will learn or apply.")
    ) # Example: ["API Integration", "Database Design", "Frontend Interactivity"]
    prerequisites = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Prerequisites'),
        help_text=_("List of skills or courses recommended before starting this project.")
    ) # Example: ["Basic Python", "Understanding of REST APIs"]
    technologies_used = models.ManyToManyField(
        ProjectTag,
        blank=True,
        related_name='projects',
        verbose_name=_('Technologies/Tags')
    )
    # Detailed instructions, requirements, user stories, etc.
    guidelines = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Project Guidelines & Requirements'),
        help_text=_("Structured details: e.g., {'user_stories': [], 'technical_requirements': [], 'submission_format': ''}")
    )
    # Links to helpful resources, documentation, starter code repositories
    resources = models.JSONField(
        default=list, blank=True,
        verbose_name=_('Helpful Resources'),
        help_text=_("List of URLs or references, e.g., [{'title': 'API Docs', 'url': '...'}].")
    )
    is_published = models.BooleanField(default=False, verbose_name=_('Is Published'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, # Can be system/AI generated
        related_name='projects_created',
        verbose_name=_('Created By (Instructor/Admin)')
    )
    # AI Generation Details
    ai_generated = models.BooleanField(default=False, verbose_name=_('AI Generated'))
    ai_generation_prompt = models.TextField(blank=True, null=True, verbose_name=_('AI Generation Prompt Used'))
    # Could add a field for course or learning path this project is associated with
    # course = models.ForeignKey('courses.Course', null=True, blank=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Project Definition')
        verbose_name_plural = _('Project Definitions')
        ordering = ['-created_at', 'title']

    def __str__(self):
        return self.title

class UserProject(models.Model):
    """
    Represents an instance of a Project assigned to or undertaken by a user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_projects',
        verbose_name=_('User')
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE, # If project definition is deleted, user's instance goes too.
                                 # Consider PROTECT if you want to prevent Project deletion if UserProjects exist.
        related_name='user_instances',
        verbose_name=_('Project Definition')
    )
    status = models.CharField(
        max_length=30,
        choices=USER_PROJECT_STATUS_CHOICES,
        default='not_started',
        verbose_name=_('Status')
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Started At'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At')) # When successfully passed assessment
    
    # User-provided links for their project
    repository_url = models.URLField(blank=True, null=True, verbose_name=_('Project Repository URL (e.g., GitHub)'))
    live_url = models.URLField(blank=True, null=True, verbose_name=_('Live Project URL (e.g., deployed app)'))

    # Could link to a specific course enrollment if project is part of a course
    # enrollment = models.ForeignKey('courses.Enrollment', null=True, blank=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Assigned/Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Last Updated At'))

    class Meta:
        verbose_name = _('User Project Instance')
        verbose_name_plural = _('User Project Instances')
        unique_together = [['user', 'project']] # User can only have one instance of a specific project definition
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return f"{self.user.email}'s work on '{self.project.title}' ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.status == 'in_progress' and not self.started_at:
            self.started_at = timezone.now()
        # completed_at is set when assessment passes
        super().save(*args, **kwargs)


class ProjectSubmission(models.Model):
    """
    Represents a user's submission for a given UserProject instance.
    A UserProject can have multiple submissions if re-attempts are allowed.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_project = models.ForeignKey(
        UserProject,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_('User Project Instance')
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Submitted At'))
    submission_notes = models.TextField(blank=True, null=True, verbose_name=_('Submission Notes by User'))
    
    # Storing links to files or code. For actual file uploads, use FileField and configure storage.
    # For simplicity, JSONField can store links to GitHub repo, zip files, etc.
    submission_artifacts = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Submission Artifacts'),
        help_text=_("e.g., {'repository_url': '...', 'live_demo_url': '...', 'file_links': ['...']}. UserProject URLs can be primary.")
    )
    # If you want to track submission versions
    submission_version = models.PositiveIntegerField(default=1, verbose_name=_('Submission Version'))


    class Meta:
        verbose_name = _('Project Submission')
        verbose_name_plural = _('Project Submissions')
        ordering = ['user_project', '-submitted_at'] # Latest submission first for a project

    def __str__(self):
        return f"Submission for '{self.user_project.project.title}' by {self.user_project.user.email} at {self.submitted_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        if not self.pk: # On first save (creation)
            # Update UserProject status to 'submitted'
            self.user_project.status = 'submitted'
            self.user_project.save(update_fields=['status', 'updated_at'])
            # Set submission version
            latest_submission = ProjectSubmission.objects.filter(user_project=self.user_project).order_by('-submission_version').first()
            if latest_submission:
                self.submission_version = latest_submission.submission_version + 1
        super().save(*args, **kwargs)


class ProjectAssessment(models.Model):
    """
    Stores the assessment results for a ProjectSubmission, typically done by an AI agent.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.OneToOneField( # Each submission has one primary assessment
        ProjectSubmission,
        on_delete=models.CASCADE,
        related_name='assessment',
        verbose_name=_('Project Submission')
    )
    assessed_by_ai = models.BooleanField(default=True, verbose_name=_('Assessed by AI Agent'))
    assessor_ai_agent_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('AI Agent Name/Version'))
    # If manual assessment is possible
    manual_assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='projects_assessed',
        verbose_name=_('Manual Assessor (if any)')
    )
    score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name=_('Assessment Score (0-100)'),
        help_text=_("Overall score given by the assessment.")
    )
    passed = models.BooleanField(default=False, verbose_name=_('Passed Assessment'))
    feedback_summary = models.TextField(blank=True, null=True, verbose_name=_('Feedback Summary'))
    # Detailed feedback, perhaps structured (e.g., criteria met, areas for improvement)
    detailed_feedback = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Detailed Feedback'),
        help_text=_("Structured feedback, e.g., {'criteria_met': [], 'improvement_points': [], 'ai_tutor_trigger_reason': '...'}")
    )
    assessed_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Assessed At'))

    class Meta:
        verbose_name = _('Project Assessment')
        verbose_name_plural = _('Project Assessments')
        ordering = ['-assessed_at']

    def __str__(self):
        status = "Passed" if self.passed else "Failed"
        return f"Assessment for '{self.submission.user_project.project.title}' (Score: {self.score or 'N/A'} - {status})"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new or 'passed' in kwargs.get('update_fields', []): # If assessment is new or 'passed' status changes
            # Update UserProject status based on assessment
            user_project = self.submission.user_project
            if self.passed:
                user_project.status = 'completed'
                user_project.completed_at = timezone.now()
            else:
                user_project.status = 'failed' # Or 'needs_revision' if you have such a state
                # AI Tutor trigger logic would be handled in the view/service that calls the AI
                # and creates this assessment. The 'ai_tutor_trigger_reason' can be set in detailed_feedback.
            user_project.save(update_fields=['status', 'completed_at', 'updated_at'])
