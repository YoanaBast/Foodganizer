from abc import ABC, abstractmethod

from planner.services import biometrics_core as core

SESSION_KEY = 'anon_biometrics'
FIELDS = ('gender', 'age', 'weight_kg', 'height_cm', 'activity_level')


class BiometricsStorage(ABC):
    @abstractmethod
    def form_kwargs(self):
        """kwargs for BiometricsForm (instance= or initial=)."""

    @abstractmethod
    def save(self, form):
        """Persist a valid BiometricsForm."""

    @abstractmethod
    def summary(self):
        """Object with bmr, tdee, target_calories, updated_at, or None."""


class DbBiometrics(BiometricsStorage):
    def __init__(self, user):
        self.user = user

    def _instance(self):
        return getattr(self.user, 'biometrics', None)

    def form_kwargs(self):
        inst = self._instance()
        return {'instance': inst} if inst else {}

    def save(self, form):
        obj = form.save(commit=False)
        obj.user = self.user
        obj.save()

    def summary(self):
        return self._instance()


class SessionBiometrics(BiometricsStorage):
    def __init__(self, session):
        self.session = session

    def _data(self):
        return self.session.get(SESSION_KEY)

    def form_kwargs(self):
        data = self._data()
        return {'initial': data} if data else {}

    def save(self, form):
        self.session[SESSION_KEY] = {k: form.cleaned_data[k] for k in FIELDS}
        self.session.modified = True

    def summary(self):
        data = self._data()
        return core.summarize(data) if data else None


def get_biometrics(request):
    if request.user.is_authenticated:
        return DbBiometrics(request.user)
    return SessionBiometrics(request.session)
