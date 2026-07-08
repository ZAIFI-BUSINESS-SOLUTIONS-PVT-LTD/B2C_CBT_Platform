# Razorpay Payment Integration - Production Hardening Checklist

## 🔒 Security & Environment Setup

### Environment Variables
- [ ] **Production Keys**: Replace test keys with live Razorpay keys in production
  ```bash
  # Required in .env or environment
  RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxx
  RAZORPAY_KEY_SECRET=your_secret_key_here
  RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
  ```

- [ ] **Secret Management**: Never commit keys to version control
  - Add `.env` to `.gitignore`
  - Use secure secret management (AWS Secrets Manager, Azure Key Vault, etc.)
  - Rotate keys periodically

### HTTPS & Domain Security
- [ ] **Force HTTPS**: Ensure all payment flows use HTTPS only
- [ ] **CORS Configuration**: Restrict allowed origins for API calls
- [ ] **CSP Headers**: Configure Content Security Policy for Razorpay checkout script

## 🛡️ Database & Model Hardening

### Constraints & Indexes
- [ ] **Add Database Constraints**:
  ```sql
  -- Add unique constraint on razorpay_order_id to prevent duplicates
  ALTER TABLE razorpay_orders ADD CONSTRAINT unique_razorpay_order_id UNIQUE (razorpay_order_id);
  
  -- Add indexes for better query performance
  CREATE INDEX idx_razorpay_orders_student_status ON razorpay_orders(student_id, status);
  CREATE INDEX idx_razorpay_orders_created_at ON razorpay_orders(created_at);
  ```

### Data Validation
- [ ] **Amount Validation**: Add model validation for positive amounts
- [ ] **Status Transitions**: Add validation for valid status transitions
- [ ] **Plan Validation**: Ensure plan names match server-side PLANS mapping

## 🔄 Webhook Implementation

### Webhook Endpoint Security
- [ ] **Signature Verification**: ✅ Implemented in webhook_views.py
- [ ] **IP Whitelisting**: Restrict webhook endpoint to Razorpay IPs
- [ ] **Rate Limiting**: Add rate limiting to prevent webhook abuse
- [ ] **Idempotency**: ✅ Implemented - webhooks handle duplicate events

### Webhook Configuration in Razorpay Dashboard
- [ ] **Set Webhook URL**: `https://yourdomain.com/api/payments/webhook/razorpay/`
- [ ] **Configure Events**:
  - `payment.captured`
  - `payment.failed`
  - `order.paid`
  - `refund.created`
  - `refund.processed`

## 📊 Monitoring & Logging

### Application Monitoring
- [ ] **Error Tracking**: Configure Sentry for payment errors
  ```python
  # In settings.py
  import sentry_sdk
  sentry_sdk.init(
      dsn="your-sentry-dsn",
      traces_sample_rate=1.0,
  )
  ```

- [ ] **Custom Metrics**: Track payment success/failure rates
- [ ] **Alert Setup**: Alert on failed payments, webhook failures

### Database Monitoring
- [ ] **Track Order Status Distribution**: Monitor pending/failed orders
- [ ] **Payment Reconciliation**: Daily reconciliation jobs
- [ ] **Failed Order Investigation**: Regular review of `remote_failed` orders

## 🔄 Reconciliation & Recovery

### Automated Reconciliation
- [ ] **Daily Job**: Set up cron job for payment reconciliation
  ```bash
  # Add to crontab
  0 2 * * * cd /path/to/project && python manage.py reconcile_payments --limit 500
  ```

- [ ] **Manual Tools**: Admin interface for investigating payment issues
- [ ] **Retry Mechanism**: For failed order creation attempts

### Data Integrity
- [ ] **Audit Trail**: Log all payment state changes
- [ ] **Backup Strategy**: Regular backups of payment data
- [ ] **Data Retention**: Policy for old payment records

## 🚀 Performance & Scalability

### Database Optimization
- [ ] **Connection Pooling**: Configure database connection pooling
- [ ] **Query Optimization**: Use select_related/prefetch_related appropriately
- [ ] **Database Partitioning**: Consider partitioning for large payment tables

### Caching Strategy
- [ ] **Subscription Status**: Cache user subscription status
- [ ] **Plan Pricing**: Cache plan configurations
- [ ] **Rate Limiting**: Implement rate limiting for payment endpoints

## 🧪 Testing Strategy

### Automated Testing
- [ ] **Unit Tests**: ✅ Comprehensive test suite implemented
- [ ] **Integration Tests**: Test with Razorpay test environment
- [ ] **Load Testing**: Test payment flow under load
- [ ] **Security Testing**: Penetration testing of payment flows

### Manual Testing Checklist
- [ ] **Happy Path**: Complete payment flow with test cards
- [ ] **Failed Payments**: Test various failure scenarios
- [ ] **Webhook Testing**: Verify webhook event handling
- [ ] **Concurrency Testing**: Multiple simultaneous payments

## 📱 Frontend Security

### Client-Side Hardening
- [ ] **Input Validation**: Validate all user inputs
- [ ] **CSP Headers**: Content Security Policy for Razorpay scripts
- [ ] **Error Handling**: User-friendly error messages without sensitive details

### User Experience
- [ ] **Loading States**: Show loading indicators during payment
- [ ] **Error Recovery**: Clear error messages and retry options
- [ ] **Mobile Optimization**: Test payment flow on mobile devices

## 🔧 Deployment Checklist

### Pre-Deployment
- [ ] **Test Environment**: Full testing with Razorpay test keys
- [ ] **Database Migration**: Apply all migrations in staging
- [ ] **Environment Variables**: Verify all required env vars are set
- [ ] **SSL Certificate**: Ensure valid SSL certificate

### Post-Deployment
- [ ] **Smoke Tests**: Verify basic payment flow works
- [ ] **Webhook Testing**: Test webhook delivery
- [ ] **Monitoring Setup**: Verify alerts and logging work
- [ ] **Performance Testing**: Check response times under load

## 🚨 Incident Response

### Monitoring & Alerts
- [ ] **Payment Failure Rate**: Alert if >5% failure rate
- [ ] **Webhook Delivery**: Alert on webhook delivery failures
- [ ] **API Response Times**: Alert on slow API responses
- [ ] **Database Issues**: Alert on connection/query issues

### Escalation Procedures
- [ ] **On-Call Rotation**: Define who handles payment issues
- [ ] **Documentation**: Runbooks for common payment issues
- [ ] **Emergency Contacts**: Razorpay support contact information
- [ ] **Rollback Plan**: Quick rollback procedures for payment issues

## 📋 Regular Maintenance

### Daily Tasks
- [ ] **Monitor Failed Payments**: Review and investigate failures
- [ ] **Check Webhook Delivery**: Ensure webhooks are being received
- [ ] **Review Error Logs**: Check for any unusual errors

### Weekly Tasks
- [ ] **Reconciliation Report**: Generate payment reconciliation report
- [ ] **Performance Review**: Check API response times and error rates
- [ ] **Security Review**: Check for any security alerts

### Monthly Tasks
- [ ] **Payment Analytics**: Analyze payment trends and success rates
- [ ] **Cost Analysis**: Review Razorpay transaction fees
- [ ] **Security Audit**: Review access logs and payment data access

## 🔗 Additional Resources

### Razorpay Documentation
- [Razorpay API Documentation](https://razorpay.com/docs/)
- [Webhook Guide](https://razorpay.com/docs/webhooks/)
- [Security Best Practices](https://razorpay.com/docs/security/)

### Django Security
- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Payment Processing Guidelines](https://owasp.org/www-project-top-ten/)

---

## 🎯 Implementation Priority

### High Priority (Immediate)
1. ✅ Webhook implementation and testing
2. ✅ Idempotent payment verification  
3. ✅ Transaction safety and error handling
4. ✅ Comprehensive unit tests
5. Environment variable security
6. HTTPS enforcement

### Medium Priority (Week 1)
1. Database constraints and indexes
2. Monitoring and alerting setup
3. Reconciliation job scheduling
4. Load testing
5. Admin interface enhancements

### Low Priority (Ongoing)
1. Performance optimization
2. Advanced analytics
3. Additional payment methods
4. Mobile app integration
5. International payment support

---

**Next Steps**: 
1. Set up production environment variables
2. Configure webhook URL in Razorpay dashboard  
3. Set up monitoring and alerting
4. Run integration tests with test keys
5. Deploy to staging for full testing