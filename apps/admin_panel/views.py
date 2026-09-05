from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User, AdminAuditLog
from apps.accounts.permissions import IsSuperAdminUser
from apps.organizations.models import Organization, OrganizationMembership
from apps.subscriptions.models import Plan, Subscription, UsageRecord, BillingTransaction
from apps.subscriptions.services import SubscriptionEntitlementService, CurrencyService
from apps.leads.models import Lead


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AdminKPIsView(APIView):
    """
    GET /api/v1/admin/kpis/
    Returns top-level business health metrics for Super Admin Dashboard.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # Users & Growth
        total_users = User.objects.count()
        recent_users = User.objects.filter(created_at__gte=thirty_days_ago).count()
        prev_period_users = User.objects.filter(created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago).count()
        
        user_growth_pct = 0.0
        if prev_period_users > 0:
            user_growth_pct = round(((recent_users - prev_period_users) / prev_period_users) * 100, 1)
        elif recent_users > 0:
            user_growth_pct = 100.0

        # Subscriptions Breakdown
        active_subs = Subscription.objects.select_related("plan").filter(status=Subscription.Status.ACTIVE)
        
        starter_users = active_subs.filter(plan__code=Plan.Code.STARTER).count()
        creator_users = active_subs.filter(plan__code=Plan.Code.CREATOR).count()
        enterprise_users = active_subs.filter(plan__code=Plan.Code.ENTERPRISE).count()
        paid_users = starter_users + creator_users + enterprise_users

        # All registered users not on a paid plan default to Free Plan
        free_users = max(0, total_users - paid_users)
        free_plan_pct = round((free_users / total_users * 100), 1) if total_users > 0 else 0.0

        # Calculate Monthly Recurring Revenue (MRR) dynamically
        mrr_usd = Decimal("0.00")
        for sub in active_subs.exclude(plan__code=Plan.Code.FREE):
            mrr_usd += sub.plan.price_usd

        # Total Revenue from verified successful transactions (convert INR to USD if applicable)
        successful_txs = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS)
        total_rev_usd = Decimal("0.00")
        for tx in successful_txs:
            if tx.currency == "INR":
                total_rev_usd += (tx.amount / Decimal("80.00"))
            else:
                total_rev_usd += tx.amount

        # Active paid subscriptions count
        active_paid_subscriptions = paid_users

        # Subscription conversion rate
        conversion_rate = round((active_paid_subscriptions / total_users * 100), 1) if total_users > 0 else 0.0

        return Response({
            "total_users": total_users,
            "user_growth_pct": user_growth_pct,
            "free_plan_users": free_users,
            "free_plan_pct": free_plan_pct,
            "starter_users": starter_users,
            "creator_users": creator_users,
            "enterprise_users": enterprise_users,
            "mrr_usd": str(mrr_usd.quantize(Decimal("0.01"))),
            "total_revenue_usd": str(total_rev_usd.quantize(Decimal("0.01"))),
            "active_subscriptions": active_paid_subscriptions,
            "conversion_rate": conversion_rate,
        })


class AdminAnalyticsView(APIView):
    """
    GET /api/v1/admin/analytics/
    Returns visualization trends for User Growth, Revenue, Plan Distribution, and Lead Usage.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        timeframe = request.query_params.get("timeframe", "30d")
        days_map = {"7d": 7, "30d": 30, "3m": 90, "6m": 180, "1y": 365}
        days = days_map.get(timeframe, 30)

        now = timezone.now()
        start_date = now - timedelta(days=days)

        # 1. User Growth Over Time
        users = User.objects.filter(created_at__gte=start_date).order_by("created_at")
        user_growth_map = {}
        for u in users:
            d_str = u.created_at.strftime("%Y-%m-%d")
            user_growth_map[d_str] = user_growth_map.get(d_str, 0) + 1

        user_growth = [{"date": k, "count": v} for k, v in sorted(user_growth_map.items())]

        # 2. Revenue Growth Over Time
        txs = BillingTransaction.objects.filter(
            status=BillingTransaction.Status.SUCCESS,
            created_at__gte=start_date
        ).order_by("created_at")
        revenue_map = {}
        for tx in txs:
            d_str = tx.created_at.strftime("%Y-%m-%d")
            revenue_map[d_str] = revenue_map.get(d_str, Decimal("0.00")) + (tx.amount or Decimal("0.00"))

        revenue_growth = [{"date": k, "amount": str(v)} for k, v in sorted(revenue_map.items())]

        # 3. Subscription Distribution
        active_subs = Subscription.objects.select_related("plan").filter(status=Subscription.Status.ACTIVE)
        total_active = active_subs.count() or 1

        dist = []
        for code in [Plan.Code.FREE, Plan.Code.STARTER, Plan.Code.CREATOR, Plan.Code.ENTERPRISE]:
            c = active_subs.filter(plan__code=code).count()
            dist.append({
                "plan_code": code,
                "plan_name": code.capitalize(),
                "count": c,
                "percentage": round((c / total_active) * 100, 1),
            })

        # 4. Lead Usage Breakdown
        total_leads = Lead.objects.count()
        leads_today = Lead.objects.filter(created_at__date=now.date()).count()
        leads_week = Lead.objects.filter(created_at__gte=now - timedelta(days=7)).count()
        leads_month = Lead.objects.filter(created_at__gte=now - timedelta(days=30)).count()

        channel_breakdown = {
            "instagram": Lead.objects.filter(source_channel="INSTAGRAM").count(),
            "whatsapp": Lead.objects.filter(source_channel="WHATSAPP").count(),
            "website": Lead.objects.filter(source_channel__in=["WEBSITE", "DIRECT"]).count(),
        }

        return Response({
            "timeframe": timeframe,
            "user_growth": user_growth,
            "revenue_growth": revenue_growth,
            "subscription_distribution": dist,
            "lead_analytics": {
                "total_leads": total_leads,
                "leads_today": leads_today,
                "leads_this_week": leads_week,
                "leads_this_month": leads_month,
                "channel_breakdown": channel_breakdown,
            }
        })


class AdminUsersView(APIView):
    """
    GET /api/v1/admin/users/
    Searchable, filterable, paginated user management table.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        plan_filter = request.query_params.get("plan", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        qs = User.objects.all().order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(owned_organizations__name__icontains=search)
            ).distinct()

        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "suspended":
            qs = qs.filter(is_active=False)

        if plan_filter:
            qs = qs.filter(owned_organizations__subscription__plan__code=plan_filter).distinct()

        total_count = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        users_slice = qs[start:end]

        results = []
        for user in users_slice:
            org = user.owned_organizations.first() or (user.organization_memberships.first().organization if hasattr(user, 'organization_memberships') and user.organization_memberships.exists() else None)
            
            sub_info = None
            usage_info = None
            if org:
                sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
                usage = SubscriptionEntitlementService.get_active_usage_record(sub)
                sub_info = {
                    "plan_code": sub.plan.code,
                    "plan_name": sub.plan.name,
                    "status": sub.status,
                    "price_usd": str(sub.plan.price_usd),
                    "price_inr": str(sub.plan.price_inr),
                    "charged_amount": str(sub.charged_amount),
                    "billing_currency": sub.billing_currency,
                    "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                }
                usage_info = {
                    "total_used": usage.total_leads_count,
                    "lead_limit": sub.plan.lead_limit,
                    "usage_percentage": usage.usage_percentage,
                }

            results.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name or user.email,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "organization_name": org.name if org else "No Organization",
                "organization_id": str(org.id) if org else None,
                "subscription": sub_info,
                "usage": usage_info,
            })

        return Response({
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "results": results,
        })


class AdminUserDetailView(APIView):
    """
    GET /api/v1/admin/users/{id}/
    Returns detailed profile, org, channels, usage, and payment history for a user.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        org = user.owned_organizations.first() or Organization.objects.filter(memberships__user=user).first()
        
        sub_info = None
        usage_info = None
        tx_history = []
        members = []
        if org:
            sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
            usage = SubscriptionEntitlementService.get_active_usage_record(sub)
            
            sub_info = {
                "id": str(sub.id),
                "plan_code": sub.plan.code,
                "plan_name": sub.plan.name,
                "status": sub.status,
                "price_usd": str(sub.plan.price_usd),
                "price_inr": str(sub.plan.price_inr),
                "charged_amount": str(sub.charged_amount),
                "billing_currency": sub.billing_currency,
                "period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
            usage_info = {
                "instagram_count": usage.instagram_lead_count,
                "whatsapp_count": usage.whatsapp_lead_count,
                "website_count": usage.website_lead_count,
                "total_used": usage.total_leads_count,
                "lead_limit": sub.plan.lead_limit,
                "usage_percentage": usage.usage_percentage,
            }

            for tx in BillingTransaction.objects.filter(subscription=sub).order_by("-created_at"):
                tx_history.append({
                    "id": str(tx.id),
                    "transaction_id": tx.provider_payment_id or str(tx.id)[:8],
                    "amount_usd": str(tx.amount),
                    "amount_inr": str(tx.amount),
                    "currency": tx.currency,
                    "status": tx.status,
                    "created_at": tx.created_at.isoformat(),
                })

            for m in OrganizationMembership.objects.filter(organization=org).select_related("user"):
                members.append({
                    "id": str(m.user.id),
                    "email": m.user.email,
                    "full_name": m.user.full_name,
                    "role": m.role,
                })

        return Response({
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "organization": {
                "id": str(org.id) if org else None,
                "name": org.name if org else "None",
                "slug": org.slug if org else None,
                "members": members,
            },
            "subscription": sub_info,
            "usage": usage_info,
            "payment_history": tx_history,
        })


class AdminUserActionView(APIView):
    """
    POST /api/v1/admin/users/{id}/action/
    Executes super admin action: suspend, reactivate, change_plan, extend_period, cancel_subscription, reset_usage.
    """
    permission_classes = [IsSuperAdminUser]

    def post(self, request, pk):
        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if not action:
            return Response({"detail": "Action parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        org = target_user.owned_organizations.first() or Organization.objects.filter(memberships__user=target_user).first()
        prev_state = {"is_active": target_user.is_active}
        new_state = {}

        if action == "suspend":
            target_user.is_active = False
            target_user.save()
            new_state["is_active"] = False
            msg = f"User {target_user.email} suspended."

        elif action == "reactivate":
            target_user.is_active = True
            target_user.save()
            new_state["is_active"] = True
            msg = f"User {target_user.email} reactivated."

        elif action == "change_plan":
            new_plan_code = request.data.get("plan_code")
            if not new_plan_code or not org:
                return Response({"detail": "Valid plan_code and user organization required."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                target_plan = Plan.objects.get(code=new_plan_code)
            except Plan.DoesNotExist:
                return Response({"detail": "Plan does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
            prev_state["plan"] = sub.plan.code
            sub.plan = target_plan
            sub.save()
            new_state["plan"] = target_plan.code
            msg = f"Subscription updated to {target_plan.name} for {target_user.email}."

        elif action == "extend_period":
            days = int(request.data.get("days", 30))
            if not org:
                return Response({"detail": "User organization required."}, status=status.HTTP_400_BAD_REQUEST)
            sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
            prev_state["period_end"] = sub.current_period_end.isoformat() if sub.current_period_end else None
            sub.current_period_end = (sub.current_period_end or timezone.now()) + timedelta(days=days)
            sub.save()
            new_state["period_end"] = sub.current_period_end.isoformat()
            msg = f"Extended subscription period by {days} days."

        elif action == "cancel_subscription":
            if not org:
                return Response({"detail": "User organization required."}, status=status.HTTP_400_BAD_REQUEST)
            sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
            prev_state["status"] = sub.status
            sub.status = Subscription.Status.CANCELLED
            sub.save()
            new_state["status"] = sub.status
            msg = f"Subscription cancelled for {target_user.email}."

        elif action == "reset_usage":
            if not org:
                return Response({"detail": "User organization required."}, status=status.HTTP_400_BAD_REQUEST)
            sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
            usage = SubscriptionEntitlementService.get_active_usage_record(sub)
            prev_state["total_leads_count"] = usage.total_leads_count
            usage.total_leads_count = 0
            usage.instagram_lead_count = 0
            usage.whatsapp_lead_count = 0
            usage.website_lead_count = 0
            usage.save()
            new_state["total_leads_count"] = 0
            msg = f"Reset lead usage for {target_user.email}."

        else:
            return Response({"detail": f"Unknown action '{action}'."}, status=status.HTTP_400_BAD_REQUEST)

        # Record Audit Log
        AdminAuditLog.objects.create(
            admin_user=request.user,
            admin_email=request.user.email,
            action=f"user_{action}",
            target_type="User",
            target_id=str(target_user.id),
            target_name=target_user.full_name or target_user.email,
            previous_state=prev_state,
            new_state=new_state,
            ip_address=get_client_ip(request),
        )

        return Response({"status": "success", "message": msg})


class AdminSubscriptionPlansView(APIView):
    """
    GET /api/v1/admin/subscriptions/plans/
    PATCH /api/v1/admin/subscriptions/plans/{id}/
    Centralized plan control center for dynamic pricing and lead limit updates.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        SubscriptionEntitlementService.seed_default_plans()
        plans = Plan.objects.all().order_by("display_order", "price_usd")
        
        results = []
        for p in plans:
            subscriber_count = Subscription.objects.filter(plan=p, status=Subscription.Status.ACTIVE).count()
            generated_rev = BillingTransaction.objects.filter(
                subscription__plan=p,
                status=BillingTransaction.Status.SUCCESS
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            results.append({
                "id": str(p.id),
                "code": p.code,
                "name": p.name,
                "description": p.description,
                "price_usd": str(p.price_usd),
                "price_inr": str(p.price_inr),
                "lead_limit": p.lead_limit,
                "billing_interval": p.billing_interval,
                "is_active": p.is_active,
                "display_order": p.display_order,
                "features": p.features,
                "active_subscribers": subscriber_count,
                "revenue_generated_usd": str(generated_rev),
            })

        return Response(results)

    def patch(self, request, pk):
        try:
            plan = Plan.objects.get(pk=pk)
        except Plan.DoesNotExist:
            return Response({"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        prev_state = {
            "name": plan.name,
            "price_usd": str(plan.price_usd),
            "price_inr": str(plan.price_inr),
            "lead_limit": plan.lead_limit,
            "is_active": plan.is_active,
        }

        price_usd = request.data.get("price_usd")
        price_inr = request.data.get("price_inr")
        lead_limit = request.data.get("lead_limit")
        name = request.data.get("name")
        description = request.data.get("description")
        is_active = request.data.get("is_active")
        features = request.data.get("features")

        # Validation
        if price_usd is not None and Decimal(str(price_usd)) < 0:
            return Response({"detail": "Price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        if price_inr is not None and Decimal(str(price_inr)) < 0:
            return Response({"detail": "Price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        if lead_limit is not None and int(lead_limit) < 0:
            return Response({"detail": "Lead limit cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)

        if price_usd is not None:
            plan.price_usd = Decimal(str(price_usd))
        if price_inr is not None:
            plan.price_inr = Decimal(str(price_inr))
        if lead_limit is not None:
            plan.lead_limit = int(lead_limit)
        if name:
            plan.name = name
        if description is not None:
            plan.description = description
        if is_active is not None:
            plan.is_active = bool(is_active)
        if features is not None and isinstance(features, list):
            plan.features = features

        plan.save()

        new_state = {
            "name": plan.name,
            "price_usd": str(plan.price_usd),
            "price_inr": str(plan.price_inr),
            "lead_limit": plan.lead_limit,
            "is_active": plan.is_active,
        }

        # Log Audit Record
        AdminAuditLog.objects.create(
            admin_user=request.user,
            admin_email=request.user.email,
            action="update_plan_config",
            target_type="Plan",
            target_id=str(plan.id),
            target_name=plan.name,
            previous_state=prev_state,
            new_state=new_state,
            ip_address=get_client_ip(request),
        )

        return Response({
            "status": "success",
            "message": f"Plan '{plan.name}' updated successfully.",
            "plan": {
                "id": str(plan.id),
                "code": plan.code,
                "name": plan.name,
                "price_usd": str(plan.price_usd),
                "price_inr": str(plan.price_inr),
                "lead_limit": plan.lead_limit,
                "is_active": plan.is_active,
            }
        })


class AdminRevenueView(APIView):
    """
    GET /api/v1/admin/revenue/
    Returns revenue metrics and transaction ledger.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        now = timezone.now()
        today = now.date()

        txs = BillingTransaction.objects.select_related("subscription__organization", "subscription__plan").all().order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            txs = txs.filter(status=status_filter)

        search = request.query_params.get("search", "").strip()
        if search:
            txs = txs.filter(
                Q(subscription__organization__name__icontains=search) |
                Q(provider_payment_id__icontains=search) |
                Q(provider_order_id__icontains=search)
            )

        total_rev = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        today_rev = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS, created_at__date=today).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        month_rev = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS, created_at__month=now.month, created_at__year=now.year).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        starter_rev = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS, subscription__plan__code=Plan.Code.STARTER).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        creator_rev = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS, subscription__plan__code=Plan.Code.CREATOR).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        enterprise_rev = BillingTransaction.objects.filter(status=BillingTransaction.Status.SUCCESS, subscription__plan__code=Plan.Code.ENTERPRISE).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        ledger = []
        for tx in txs[:50]:
            ledger.append({
                "id": str(tx.id),
                "transaction_id": tx.provider_payment_id or str(tx.id)[:8],
                "organization_name": tx.subscription.organization.name if tx.subscription and tx.subscription.organization else "N/A",
                "plan_name": tx.subscription.plan.name if tx.subscription and tx.subscription.plan else "N/A",
                "amount_usd": str(tx.amount),
                "amount_inr": str(tx.amount),
                "currency": tx.currency,
                "status": tx.status,
                "payment_provider": tx.provider.capitalize() if tx.provider else "Razorpay",
                "created_at": tx.created_at.isoformat(),
            })

        return Response({
            "summary": {
                "total_revenue_usd": str(total_rev),
                "today_revenue_usd": str(today_rev),
                "month_revenue_usd": str(month_rev),
                "starter_revenue_usd": str(starter_rev),
                "creator_revenue_usd": str(creator_rev),
                "enterprise_revenue_usd": str(enterprise_rev),
            },
            "ledger": ledger,
        })


class AdminSystemView(APIView):
    """
    GET /api/v1/admin/system/
    Returns system overview and recent activity feed.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        recent_activity = []

        # Recent registrations
        for u in User.objects.order_by("-created_at")[:5]:
            recent_activity.append({
                "id": f"user-{u.id}",
                "type": "registration",
                "title": "New User Registered",
                "description": f"{u.full_name or u.email} joined Nextora.",
                "timestamp": u.created_at.isoformat(),
            })

        # Recent payments
        for tx in BillingTransaction.objects.select_related("subscription__organization").filter(status=BillingTransaction.Status.SUCCESS).order_by("-created_at")[:5]:
            recent_activity.append({
                "id": f"tx-{tx.id}",
                "type": "payment",
                "title": "Payment Received",
                "description": f"Received {tx.currency} {tx.amount} for {tx.subscription.organization.name if tx.subscription and tx.subscription.organization else 'Organization'}.",
                "timestamp": tx.created_at.isoformat(),
            })

        # Recent audit logs
        for log in AdminAuditLog.objects.order_by("-created_at")[:5]:
            recent_activity.append({
                "id": f"audit-{log.id}",
                "type": "audit",
                "title": f"Admin Action: {log.action}",
                "description": f"{log.admin_email} performed {log.action} on {log.target_name}.",
                "timestamp": log.created_at.isoformat(),
            })

        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)

        return Response({
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "suspended_users": User.objects.filter(is_active=False).count(),
            "total_workspaces": Organization.objects.count(),
            "total_leads_captured": Lead.objects.count(),
            "recent_activity": recent_activity[:15],
        })


class AdminAuditLogsView(APIView):
    """
    GET /api/v1/admin/audit-logs/
    Returns administrative activity logs.
    """
    permission_classes = [IsSuperAdminUser]

    def get(self, request):
        logs = AdminAuditLog.objects.all().order_by("-created_at")[:100]
        results = []
        for log in logs:
            results.append({
                "id": str(log.id),
                "admin_email": log.admin_email,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "target_name": log.target_name,
                "previous_state": log.previous_state,
                "new_state": log.new_state,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            })
        return Response(results)
