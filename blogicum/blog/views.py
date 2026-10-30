from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Post, Category

User = get_user_model()


def get_posts_queryset():
    """
    Вспомогательная функция: возвращает QuerySet постов 
    с оптимизацией (select_related) и аннотацией количества комментариев.
    """
    return Post.objects.select_related(
        'category', 'author', 'location'
    ).annotate(comment_count=Count('comments'))


def index(request):
    """Главная страница: последние опубликованные посты с пагинацией."""
    template = 'blog/index.html'
    
    posts = get_posts_queryset().filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True
    ).order_by('-pub_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    return render(request, template, context)


def post_detail(request, post_id):
    """Страница отдельного поста с проверкой прав для автора."""
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
        
    context = {'post': post}
    return render(request, template, context)


def category_posts(request, category_slug):
    """Страница категории: опубликованные посты категории с пагинацией."""
    template = 'blog/category.html'
    
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    
    posts = get_posts_queryset().filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).order_by('-pub_date')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    """Страница профиля пользователя."""
    template = 'blog/profile.html'
    
    # Получаем пользователя или возвращаем 404
    user_profile = get_object_or_404(User, username=username)
    
    # Проверяем, является ли текущий пользователь владельцем профиля
    is_author = request.user == user_profile
    
    # Базовый QuerySet постов этого автора с аннотацией комментариев
    posts = get_posts_queryset().filter(author=user_profile)
    
    # Если пользователь НЕ автор, показываем только опубликованные посты
    if not is_author:
        posts = posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )
    
    posts = posts.order_by('-pub_date')
    
    # Настраиваем пагинацию (10 постов на страницу)
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': user_profile,
        'page_obj': page_obj,
    }
    return render(request, template, context)


class UserRegistrationView(CreateView):
    """Представление для регистрации нового пользователя."""
    form_class = UserCreationForm
    success_url = reverse_lazy('blog:index')
    template_name = 'registration/registration_form.html'