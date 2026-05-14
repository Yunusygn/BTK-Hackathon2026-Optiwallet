"""
Database Models.

Tüm SQLAlchemy modelleri burada toplanır.
Alembic autogenerate için **mutlaka** import edilmeleri gerekiyor.

Domain Bazlı Organizasyon:
- user.py        → Auth & Identity (User, OAuth, Session, 2FA)
- profile.py     → Personal & Financial Profile (Profile, FinancialProfile, Preferences)
- finance.py     → Money Management (Cards, Coupons, Goals, Expenses, Budget, Recurring)
- conversation.py → Chat & AI (Folders, Conversations, Messages, Recommendations, Favorites, Comparisons)
- notification.py → Notifications & Audit (Settings, Notifications, Push, Audit Logs)

Toplam: 20+ tablo
"""

# ===== User & Auth =====
from app.models.user import (
    OAuthAccount,
    OAuthProvider,
    Session,
    TwoFactorSecret,
    User,
    UserRole,
)

# ===== Profile =====
from app.models.profile import (
    FinancialProfile,
    Gender,
    MaritalStatus,
    Occupation,
    PaymentPreference,
    Preferences,
    Profile,
)

# ===== Finance =====
from app.models.finance import (
    BankCode,
    Budget,
    CardType,
    Coupon,
    CouponType,
    CreditCard,
    Expense,
    ExpenseCategory,
    FinancialGoal,
    GoalStatus,
    RecurringFrequency,
    RecurringPayment,
)

# ===== Conversation & AI =====
from app.models.conversation import (
    AgentName,
    AlertType,
    Comparison,
    Conversation,
    ConversationStatus,
    Favorite,
    FavoriteFolder,
    FeedbackRating,
    Folder,
    Message,
    MessageFeedback,
    MessageRole,
    PriceAlert,
    PriceHistory,
    Recommendation,
)

# ===== Notification & Audit =====
from app.models.notification import (
    AuditAction,
    AuditLog,
    Notification,
    NotificationChannel,
    NotificationFrequency,
    NotificationSettings,
    NotificationStatus,
    NotificationType,
    PushSubscription,
)

__all__ = [
    # ===== User & Auth =====
    "User",
    "UserRole",
    "OAuthAccount",
    "OAuthProvider",
    "Session",
    "TwoFactorSecret",
    # ===== Profile =====
    "Profile",
    "FinancialProfile",
    "Preferences",
    "Gender",
    "MaritalStatus",
    "Occupation",
    "PaymentPreference",
    # ===== Finance =====
    "CreditCard",
    "Coupon",
    "FinancialGoal",
    "Expense",
    "Budget",
    "RecurringPayment",
    "BankCode",
    "CardType",
    "CouponType",
    "ExpenseCategory",
    "GoalStatus",
    "RecurringFrequency",
    # ===== Conversation =====
    "Folder",
    "Conversation",
    "Message",
    "MessageFeedback",
    "Recommendation",
    "FavoriteFolder",
    "Favorite",
    "PriceHistory",
    "PriceAlert",
    "Comparison",
    "ConversationStatus",
    "MessageRole",
    "AgentName",
    "FeedbackRating",
    "AlertType",
    # ===== Notification =====
    "Notification",
    "NotificationSettings",
    "PushSubscription",
    "AuditLog",
    "NotificationType",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationFrequency",
    "AuditAction",
]