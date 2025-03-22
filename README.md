# Enhanced Shinigami Eyes

An enhanced version of the Shinigami Eyes Chrome/Firefox addon that uses machine learning to identify and highlight transphobic/anti-LGBT and trans-friendly content across various platforms.

## Overview

This enhanced version builds upon the original Shinigami Eyes addon, which highlights transphobic/anti-LGBT and trans-friendly subreddits, users, Facebook pages, and groups with different colors. The enhanced version adds:

- **ML-powered analysis** using a custom-trained Gemma 3:4b model for content classification
- **Gray area highlighting** for content requiring further investigation
- **Common Crawl integration** for semantic web analysis
- **Improved color schemes** for better readability across light and dark themes
- **Opt-in auto-marking** based on user-defined criteria

Original links:

- [Shinigami Eyes for Chrome](https://chrome.google.com/webstore/detail/ijcpiojgefnkmcadacmacogglhjdjphj/)
- [Shinigami Eyes for Firefox](https://addons.mozilla.org/en-US/firefox/addon/shinigami-eyes/)

![Original Screenshot](https://raw.githubusercontent.com/shinigami-eyes/shinigami-eyes/master/images/preview.png)

## New Features

### Multi-point Classification System

Content is now classified on a three-point scale:

- **Trans-friendly** (0): Indicated with green highlighting
- **Gray area** (1): Content that needs further investigation, indicated with yellow highlighting
- **Transphobic** (2): Indicated with red highlighting

### AI-powered Content Analysis

The extension now uses a custom-trained Gemma 3:4b model to analyze content and determine its classification. The ML service provides:

- Text analysis for posts and comments
- Profile analysis for more accurate user classification
- URL content analysis for linked websites

### Common Crawl Integration

The extension integrates with Common Crawl data to provide:

- Historical web context for classification
- Analysis of linked websites for better context verification
- Semantic web analysis to understand related content

### Improved User Interface

- Adaptive color schemes for both light and dark themes
- Clear visualization of gray area content
- Confidence indicators for classifications

## Installation

See the [setup guide](guide/setup.md) for detailed installation instructions.

## Training Your Own Model

If you want to train your own classification model, see the [training guide](guide/training.md).

## Web Analysis

Learn about the web analysis features in the [web analysis guide](guide/web_analysis.md).

## Privacy

This enhanced version is designed with privacy in mind:

- All processing is done locally using Ollama
- No user data is sent to Google or Microsoft services
- All features are opt-in, giving users full control over their experience

## Dependencies

- Ollama for running the Gemma 3:4b model
- PyTorch for custom model training and analysis
- Flask for the ML service API
- Common Crawl for semantic web analysis

## License

This project maintains the original license of the Shinigami Eyes project.
