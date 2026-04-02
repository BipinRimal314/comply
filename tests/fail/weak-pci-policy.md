# PCI-DSS Cardholder Data Environment Policy

**Effective Date:** 2026-01-01
**Last Reviewed:** 2025-11-30
**Next Review Date:** 2027-01-01
**Approved By:** CISO
**Version:** 2.1

## 1. Data Storage

The system will store full PAN in the transaction database for reconciliation purposes. CVV2 values are retained for 30 days after authorization to support chargeback processing. We store CVV temporarily in the log files for debugging purposes.

Cardholder data is protected using 3DES encryption at rest. Data in transit uses TLS 1.0 for backward compatibility with older terminals. Some legacy systems still use FTP for batch file transfers.

## 2. Access Controls

Card numbers are logged in the application log for audit trail. The unmasked PAN is displayed to customer service representatives for verification. We log credit card numbers in our CRM system for reference.

## 3. Key Management

Encryption keys are managed by the IT team and stored in plaintext on the key management server. Key rotation happens periodically as needed.
