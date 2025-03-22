# Web Analysis Features in Enhanced Shinigami Eyes

This document provides an overview of the web analysis features in the enhanced Shinigami Eyes extension, including the Common Crawl integration.

## Overview

The enhanced Shinigami Eyes extension includes sophisticated web analysis features that help classify content and accounts more accurately. These features analyze:

1. **Profile content** across multiple platforms
2. **Website content** from URLs shared or linked by accounts
3. **Historical web data** via Common Crawl integration

## Supported Platforms

The web analyzer supports the following platforms:

- Twitter/X
- Reddit
- Facebook (limited due to privacy restrictions)
- YouTube
- Mastodon
- Medium
- BlueSky
- Generic websites

## Features

### Profile Analysis

The profile analyzer can:

- Fetch and analyze recent posts from a user's profile
- Analyze shared links to determine context
- Determine the likelihood of transphobic content based on language patterns
- Provide confidence scores for classifications

### Common Crawl Integration

[Common Crawl](https://commoncrawl.org/) is a non-profit organization that builds and maintains an open repository of web crawl data that can be accessed and analyzed by anyone. Our integration:

- Analyzes websites using historical data from Common Crawl
- Identifies patterns in content from websites frequently shared by analyzed accounts
- Provides semantic web analysis to understand linked content
- Improves classification accuracy for accounts that don't post explicit content but share problematic links

### Classification Enhancement

The web analysis tools enhance classification by:

- Providing additional signals beyond direct text analysis
- Identifying patterns of behavior across platforms
- Looking at the wider context of shared content
- Building a more comprehensive picture of an account's stance

## Privacy and Ethics

All web analysis features respect privacy and ethical guidelines:

- No personal data is stored beyond temporary caching for performance
- Analysis is limited to publicly available content
- The system does not attempt to de-anonymize users
- All analysis is performed on the server side with secure protocols

## Opt-in Auto-Marking

The auto-marking feature is strictly opt-in and uses web analysis to:

- Automatically mark related accounts based on their content
- Identify linked accounts that share similar patterns
- Apply appropriate classifications with confidence thresholds
- Allow users complete control over which auto-marking features they enable

## Technical Details

The web analysis system uses:

- BeautifulSoup for HTML parsing
- WARC file processing for Common Crawl data
- Cached requests to minimize API load
- Platform-specific fetchers for optimal data retrieval
- Regex pattern matching for preliminary analysis
- Integration with the ML model for deeper content analysis

## Configuration Options

Users can configure web analysis features through the extension settings:

- Enable/disable profile analysis
- Enable/disable Common Crawl integration
- Set confidence thresholds for auto-marking
- Choose which platforms to analyze
- Set cache duration for analysis results

## Limitations

Current limitations include:

- Facebook data access is highly restricted due to platform policies
- Some platforms may block automated access
- Historical data may not reflect recent changes in account behavior
- Analysis quality depends on the availability of public content

## Future Improvements

Planned improvements include:

- More sophisticated content analysis
- Additional platform support
- Improved handling of multilingual content
- Enhanced pattern recognition for subtle indicators
- More detailed classification explanations
