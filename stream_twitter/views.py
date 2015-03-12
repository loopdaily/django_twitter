from django.views.generic.edit import CreateView
from django.shortcuts import render_to_response, render, get_object_or_404,\
    redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.template.context import RequestContext
from stream_django.enrich import Enrich
from stream_django.feed_manager import feed_manager
from stream_twitter.models import Follow
from stream_twitter.models import Tweet, Hashtag
from pytutorial import settings


enricher = Enrich()


class TimelineView(CreateView):
    model = Tweet
    fields = ['text']
    success_url = "/timeline/"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(TimelineView, self).form_valid(form)

    def get(self, request):
        feeds = feed_manager.get_news_feeds(request.user.id)
        activities = feeds.get('flat').get()['results']
        activities = enricher.enrich_activities(activities)
        hashtags = Hashtag.objects.order_by('-occurrences')
        context = {
            'activities': activities,
            'form': self.get_form_class(),
            'login_user': request.user,
            'hashtags': hashtags
        }
        return render(request, 'stream_twitter/timeline.html', context)


class DiscoverView(CreateView):
    #TODO: Remove post method, allow this view to destroy as well
    model = Follow
    fields = ['target']
    success_url = "/timeline/"

    def get(self, request):
        users = User.objects.order_by('-date_joined')
        login_user = User.objects.get(username=request.user)
        following = []
        for i in users:
            if len(i.followers.filter(user=login_user.id)) == 0:
                following.append((i, False))
            else:
                following.append((i, True))
        login_user = User.objects.get(username=request.user)
        context = {
            'users': users,
            'form': self.get_form_class(),
            'login_user': request.user,
            'following': following
        }
        return render(request, 'stream_twitter/follow_form.html', context)

    def form_valid(self, form, *args, **kwargs):
        form.instance.user = self.request.user
        return super(DiscoverView, self).form_valid(form)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            follow, created = Follow.objects.get_or_create(
                user=request.user,
                target_id=request.POST['target']
            )
            if not created:
                follow.delete()
        return redirect(self.success_url)


class HomeView(CreateView):
    greeting = "Welcome to Stream Twitter"

    def get(self, request):
        if not request.user.is_authenticated() and not settings.USE_AUTH:
            # hack to log you in automatically for the demo app
            # #TODO: move username and password to settings
            admin_user = authenticate(
                username='theRealAlbert', password='1234')
            auth_login(request, admin_user)
        context = RequestContext(request)
        context_dict = {
            'greeting': self.greeting,
            'login_user': request.user,
            'users': User.objects.order_by('-date_joined')
        }
        return render_to_response('stream_twitter/home.html', context_dict, context)


def user(request, user_name):
    user = get_object_or_404(User, username=user_name)
    feeds = feed_manager.get_user_feed(user.id)
    activities = feeds.get()['results']
    activities = enricher.enrich_activities(activities)
    context = {
        'activities': activities,
        'user': user,
        'login_user': request.user
    }
    return render(request, 'stream_twitter/user.html', context)


def hashtag(request, hashtag_name):
    hashtag_name = hashtag_name.lower()
    feed = feed_manager.get_feed('hashtag', hashtag_name)
    activities = feed.get(limit=25)['results']

    activities = enricher.enrich_activities(activities)
    context = {
        'hashtag_name': hashtag_name,
        'activities': activities
    }
    return render(request, 'stream_twitter/hashtag.html', context)
