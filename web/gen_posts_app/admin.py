from django.contrib import admin
from .import models

@admin.register(models.BlogArticle)
class BlogArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'views_count', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content')


@admin.register(models.PostContent)
class PostContentAdmin(admin.ModelAdmin):
    pass



@admin.register(models.PostIdea)
class PostIdeaAdmin(admin.ModelAdmin):
    pass