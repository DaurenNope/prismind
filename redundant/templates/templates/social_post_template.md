---
title: "{{ post.author }} - {{ analysis.summary[:50] }}..."
platform: {{ post.platform }}
author: "{{ post.author }}"
author_handle: "{{ post.author_handle }}"
category: {{ analysis.category }}
subcategory: {{ analysis.subcategory }}
content_type: {{ analysis.content_type }}
sentiment: {{ analysis.sentiment }}
value_score: {{ analysis.value_score }}
created_date: {{ post.created_at.strftime('%Y-%m-%d') }}
saved_date: {{ post.saved_at.strftime('%Y-%m-%d') if post.saved_at else 'Unknown' }}
analyzed_date: {{ analysis.get('analyzed_at', 'Unknown') | timestamp_to_date if analysis.get('analyzed_at') else 'Unknown' }}
confidence: {{ analysis.get('confidence_score', 0.0) }}
tags: [{{ analysis.get('tags', []) | join(', ') }}{% if post.hashtags %}, {{ post.hashtags | join(', ') }}{% endif %}]
---

# {{ post.author }} on {{ post.platform | title }}

## Summary
{{ analysis.summary }}

## Original Content
{% if post.post_type == 'thread' %}
**🧵 Thread Content:**

{{ post.content | replace('\n\n', '\n\n---\n\n') }}
{% else %}
> {{ post.content | replace('\n', '\n> ') }}
{% endif %}

{% if post.media_urls %}
## Media
{% for media_url in post.media_urls %}
- ![Media]({{ media_url }})
{% endfor %}
{% endif %}

## Analysis

**Category:** {{ analysis.category }} → {{ analysis.subcategory }}
**Content Type:** {{ analysis.content_type }}
**Sentiment:** {{ analysis.sentiment }}
**Value Score:** {{ analysis.value_score }}/10

{% if analysis.get('topics') %}
### Key Topics
{% for topic in analysis.topics %}
- {{ topic }}
{% endfor %}
{% endif %}

{% if analysis.get('key_insights') %}
### Key Insights
{% for insight in analysis.key_insights %}
- {{ insight }}
{% endfor %}
{% endif %}

{% if analysis.get('action_items') %}
### Action Items
{% for action in analysis.action_items %}
- [ ] {{ action }}
{% endfor %}
{% endif %}

{% if analysis.get('related_concepts') %}
### Related Concepts
{% for concept in analysis.related_concepts %}
- [[{{ concept }}]]
{% endfor %}
{% endif %}

## Engagement Metrics
{% for metric, value in post.engagement.items() %}
- **{{ metric.title() }}:** {{ value }}
{% endfor %}

## Metadata
- **Platform:** {{ post.platform | title }}
- **Author:** {{ post.author }} ({{ post.author_handle }})
- **Created:** {{ post.created_at.strftime('%Y-%m-%d %H:%M:%S') }}
- **Saved:** {{ post.saved_at.strftime('%Y-%m-%d %H:%M:%S') if post.saved_at else 'Unknown' }}
- **Original URL:** [View Original]({{ post.url }})
- **Save Reason:** {{ analysis.get('save_reason', 'User saved this content') }}

{% if post.hashtags %}
## Original Hashtags
{% for hashtag in post.hashtags %}
#{{ hashtag }} 
{% endfor %}
{% endif %}

{% if post.mentions %}
## Mentions
{% for mention in post.mentions %}
- {{ mention }}
{% endfor %}
{% endif %}

---
*Analyzed with AI on {{ analysis.get('analyzed_at', 'Unknown') | timestamp_to_date if analysis.get('analyzed_at') else 'Unknown' }}*
*Confidence: {{ analysis.get('confidence_score', 0.0) }}/1.0* 