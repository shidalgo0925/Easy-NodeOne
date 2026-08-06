# Event Catalog (EIS)

| Campo | Valor |
|-------|--------|
| Versión | **1.0.0** |
| Norma | EIS-004 |

| event_type | capability | Descripción | Emisor candidato |
|------------|------------|-------------|------------------|
| `Commerce.OrderCreated` | `commerce.events` | Pedido creado | EPosOne / EN1 |
| `Commerce.OrderPaid` | `commerce.events` | Pedido cobrado | EPosOne |
| `Commerce.PaymentReceived` | `payment.events` | Pago registrado | EPosOne / EN1 |
| `Commerce.CashShiftClosed` | `commerce.events` | Turno cerrado | EPosOne |
| `Commerce.CashShiftOpened` | `commerce.events` | Turno abierto | EPosOne |
| `License.LicenseExpired` | `license.events` | Licencia vencida | EPosOne / EN1 |
| `License.LicenseChanged` | `license.events` | Cambio estado licencia | EPosOne |
| `Membership.MembershipApproved` | `membership.events` | Membresía aprobada | EN1 / Relatic |
| `Membership.MemberVerified` | `membership.events` | Verificación API | EN1 |
| `Subscription.SubscriptionChanged` | `subscription.events` | Cambio suscripción ETS | EN1 |
| `Marketing.CampaignPublished` | `marketing.events` | Campaña publicada | ARP |
| `Marketing.CampaignPerformanceUpdated` | `marketing.events` | Métricas campaña | ARP |
| `Audit.HistoryRecorded` | `audit.events` | Acción auditada | EN1 |
| `Identity.UserSignedIn` | `identity.events` | Login (si se publica) | EN1 / ARP |

### Aliases conocidos (productos)

| Legacy / producto | Canónico EIS |
|-------------------|--------------|
| `eposone.order.created` | `Commerce.OrderCreated` |
| `eposone.order.paid` | `Commerce.OrderPaid` |
| `commerce.cash.shift.closed` (si existe) | `Commerce.CashShiftClosed` |
