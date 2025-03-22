# Hosted Backend for Enhanced Shinigami Eyes

This guide explains how to use the hosted backend service for Enhanced Shinigami Eyes, which provides machine learning features without requiring you to set up your own server.

## About the Hosted Service

The Enhanced Shinigami Eyes hosted service provides:

1. Machine learning-based classification of content
2. Profile analysis across multiple platforms
3. Common Crawl integration for semantic web analysis
4. Gray area detection for ambiguous content
5. Confidence indicators for classifications

All of these features are provided while respecting your privacy:

- **No user data collection**: We don't collect any data that could identify users of the extension
- **No content logging**: Content analyzed by the service is not stored
- **Transparent codebase**: All code is open source and can be audited

## Using the Hosted Backend

To use the hosted backend:

1. Open the Enhanced Shinigami Eyes settings page (click the extension icon and select "Settings")
2. Under "Backend Configuration", select "Enhanced - Hosted Backend"
3. Click "Save Settings"

That's it! The extension will now use the hosted service for enhanced features.

## Supporting the Service

The hosted service is provided free of charge to all users. However, running machine learning models at scale requires server resources. If you find the enhanced features valuable, please consider supporting the service with a small donation:

- **One-time donations**: Help cover server costs with a one-time contribution
- **Monthly support**: Provide ongoing support with a small monthly donation

The extension will show a donation prompt once every 30 days. After 5 donations (one-time or recurring), the prompts will stop permanently.

All donations are handled securely via Stripe, and we don't collect any personal information in the process.

## Privacy Considerations

The hosted backend operates with these privacy principles:

1. **No personal data collection**: We don't collect usernames, IP addresses, or any other identifying information
2. **Transient processing**: Content you analyze is processed in memory and never stored permanently
3. **No tracking**: We don't use cookies or other tracking mechanisms
4. **Limited analytics**: Only anonymous, aggregate statistics are collected (total requests per day)
5. **Secure communication**: All communication uses HTTPS encryption

## Self-Hosting Alternative

If you prefer maximum control and privacy, you can also choose to self-host the backend service on your own computer. This requires more technical setup but gives you complete control.

To learn how to set up a local backend, see the [Self-Hosting Guide](setup.md).

## FAQ

**Q: Is my browsing history or viewed content shared with the service?**  
A: No. The extension only sends specific content for analysis when you opt to use the enhanced features.

**Q: How much does the service cost?**  
A: The service is free for all users. Donations are completely optional.

**Q: Can I switch between hosted and local backends?**  
A: Yes, you can change your backend setting at any time through the extension settings.

**Q: What if the hosted service goes offline?**  
A: The extension will automatically fall back to legacy mode if it can't connect to the hosted service.

**Q: How often will I be asked to donate?**  
A: At most once every 30 days, and only if you're using the hosted backend. After 5 donations, you'll never see donation prompts again.

**Q: Are there usage limits for the hosted service?**  
A: To ensure fair usage, there's a limit of 60 requests per minute per user. This is far above typical usage patterns.
