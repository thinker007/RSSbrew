from django.core.management.base import BaseCommand
from django.utils import timezone
from FeedManager.models import ProcessedFeed, Article, Digest
from datetime import timedelta
import logging

logger = logging.getLogger('feed_logger')

class Command(BaseCommand):
    help = 'Generate digest for each processed feed.'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--feed', type=int, help='ID of the ProcessedFeed to update')

    def handle(self, *args, **options):
        feed_id = options.get('feed')
        if feed_id:
            try:
                feed = ProcessedFeed.objects.get(id=feed_id)
                self.gen_digest(feed)
                logger.info(f'Generating digest for feed: {feed.name} at {timezone.now()}')
            except ProcessedFeed.DoesNotExist:
                raise CommandError(f'ProcessedFeed with ID {feed_id} does not exist.')
        else:
            processed_feeds = ProcessedFeed.objects.filter(toggle_digest=True)
            for feed in processed_feeds:
                logger.info(f'Generating digest for feed: {feed.name} at {timezone.now()}')
                self.gen_digest(feed)

    def gen_digest(self, feed):
        now = timezone.now()
        last_digest = feed.last_digest
        delta = timedelta(days=0.5) if feed.digest_frequency == 'daily' else timedelta(days=6.5)
        #logger.debug(f"Last digest: {last_digest})")
        if not last_digest or now - last_digest > delta:
            start_time = last_digest if last_digest else now - delta
            articles = Article.objects.filter(
                original_feed__processed_feeds=feed,
                published_date__gte=start_time,
                published_date__lte=now
            ).order_by('original_feed', '-published_date')
        
            if not articles.exists():
                logger.info(f"No new articles for feed {feed.name} since last digest.")
                return

            digest_content = self.format_digest(articles)
            digest = Digest(processed_feed=feed, content=digest_content)
            digest.save()
            logger.info(f"Digest for {feed.name} created.")
            feed.last_digest = now
            feed.save()

    def format_digest(self, articles):
        current_feed = None
        digest_builder = []
        for article in articles:
            if current_feed != article.original_feed:
                if current_feed is not None:
                    digest_builder.append("\n\n")  # Add separation between feeds
                current_feed = article.original_feed
                digest_builder.append(f"<h2>{current_feed.title}</h2>")
            digest_builder.append(f"<li><a href='{article.url}'>{article.title}</a></li>")
            if article.summary_one_line:
                digest_builder.append(f"<ul><blockquote>{article.summary_one_line}</blockquote></ul>")

        return ''.join(digest_builder)
