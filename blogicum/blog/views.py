from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required

from .models import Post, Category, Comment
from .forms import PostForm, CommentForm

User = get_user_model()


def get_posts_queryset():
    """Вспомогательная функция: возвращает QuerySet постов с оптимизацией и аннотацией."""
    return Post.objects.select_related(
        'category', 'author', 'location'
    ).annotate(comment_count=Count('comments'))


def index(request):
    template = 'blog/index.html'
    posts = get_posts_queryset().filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True
    ).order_by('-pub_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, template, {'page_obj': page_obj})


def post_detail(request, post_id):
    template = 'blog/detail.html'
    post = get_object_or_404(get_posts_queryset(), pk=post_id)
    
    if request.user != post.author:
        post = get_object_or_404(
            Post.objects.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            ),
            pk=post_id
        )
    
    comments = post.comments.select_related('author').order_by('created_at')
    
    # ДОБАВЛЕНО: создаём пустую форму для комментариев, чтобы шаблон мог её отрисовать
    form = CommentForm()
    
    context = {
        'post': post, 
        'comments': comments,
        'form': form  # ДОБАВЛЕНО: передаём форму в контекст
    }
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    
    posts = get_posts_queryset().filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).order_by('-pub_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, template, {'category': category, 'page_obj': page_obj})


def profile(request, username):
    template = 'blog/profile.html'
    user_profile = get_object_or_404(User, username=username)
    is_author = request.user == user_profile
    
    posts = get_posts_queryset().filter(author=user_profile)
    if not is_author:
        posts = posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )
    posts = posts.order_by('-pub_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, template, {'profile': user_profile, 'page_obj': page_obj})


@login_required
def edit_profile(request):
    """Страница редактирования профиля пользователя."""
    template = 'blog/user.html'
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('blog:profile', username=user.username)
    else:
        form = UserChangeForm(instance=request.user)
    return render(request, template, {'form': form})


class UserRegistrationView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('blog:index')
    template_name = 'registration/registration_form.html'


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
        
    def get_success_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
        
    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        
    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.pk})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
        
    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        
    def get_success_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем существование поста перед созданием комментария
        get_object_or_404(Post, pk=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post_id = self.kwargs['post_id']
        return super().form_valid(form)
        
    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})

class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    
    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author
        
    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        
    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.post.pk})


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    
    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author
        
    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        
    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.post.pk})