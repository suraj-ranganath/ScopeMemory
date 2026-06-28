export const STATIC_DEMO_SNAPSHOT = {
  "captured_at": "2026-06-28T08:23:52.045Z",
  "source": "seeded-local-backend-before-tunnel-shutdown",
  "session_id": "sess_demo_001",
  "agent_id": "agent_renewal_01",
  "health": {
    "status": "ok",
    "stack": "dolt+graph+policy+mcp",
    "graph_backend": "memgraph",
    "recipe_retrieval": "memgraph",
    "policy_engine": "cozo-datalog-required",
    "iam_mode": "http",
    "delegation_jwt_required": "true",
    "mcp_endpoint": "/mcp"
  },
  "uiState": {
    "session": {
      "session_id": "sess_demo_001",
      "user_id": "user_alice",
      "team_id": "team_sales",
      "agent_id": "agent_renewal_01",
      "goal": "Prepare renewal follow-up for Acme. Check recent Slack context and create a Linear issue.",
      "goal_class": "sales_renewal_prep",
      "status": "waiting_for_human",
      "created_at": "2026-06-28T08:23:51"
    },
    "recipe_hits": [
      {
        "recipe_id": "recipe_sales_renewal_v3",
        "score": 0.89,
        "title": "Sales Renewal Prep v3"
      }
    ],
    "predicted_tools": [
      "linear.add_comment",
      "linear.create_issue",
      "linear.search_issues",
      "slack.search_messages"
    ],
    "predicted_scopes": [
      "linear:comments:create",
      "linear:issues:create",
      "linear:issues:read",
      "slack:channels:history"
    ],
    "access_requests": [
      {
        "request_id": "req_1c0613c6630b",
        "session_id": "sess_demo_001",
        "user_id": "user_alice",
        "requested_scope": "slack:channels:history",
        "requested_resource": "slack_channel:sales-acme",
        "requested_tool_id": "slack.search_messages",
        "reason": "Preflight predicted this human-required scope from governed recipe memory (recipe_sales_renewal_v3).",
        "recipe_id": "recipe_sales_renewal_v3",
        "status": "pending",
        "approver_id": null,
        "created_at": "2026-06-28T08:23:51",
        "agent_id": "agent_renewal_01",
        "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
        "approver_type": "human",
        "expires_at": null,
        "request_origin": "preflight_prediction",
        "prediction_id": "pred_188fea7515bd",
        "prediction_confidence": 0.89,
        "source_trace_ids_json": "[\"recipe_sales_renewal_v3\"]",
        "trigger_phase": "preflight",
        "created_before_tool_call": true,
        "sent_at": "2026-06-28T08:23:51",
        "first_tool_call_at": null,
        "source_trace_ids": [
          "recipe_sales_renewal_v3"
        ]
      }
    ],
    "anticipated_requests": [
      {
        "request_id": "req_1c0613c6630b",
        "session_id": "sess_demo_001",
        "user_id": "user_alice",
        "requested_scope": "slack:channels:history",
        "requested_resource": "slack_channel:sales-acme",
        "requested_tool_id": "slack.search_messages",
        "reason": "Preflight predicted this human-required scope from governed recipe memory (recipe_sales_renewal_v3).",
        "recipe_id": "recipe_sales_renewal_v3",
        "status": "pending",
        "approver_id": null,
        "created_at": "2026-06-28T08:23:51",
        "agent_id": "agent_renewal_01",
        "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
        "approver_type": "human",
        "expires_at": null,
        "request_origin": "preflight_prediction",
        "prediction_id": "pred_188fea7515bd",
        "prediction_confidence": 0.89,
        "source_trace_ids_json": "[\"recipe_sales_renewal_v3\"]",
        "trigger_phase": "preflight",
        "created_before_tool_call": true,
        "sent_at": "2026-06-28T08:23:51",
        "first_tool_call_at": null,
        "source_trace_ids": [
          "recipe_sales_renewal_v3"
        ]
      }
    ],
    "grants": [
      {
        "grant_id": "grant_linear_001",
        "session_id": "sess_demo_001",
        "scope": "linear:issues:create",
        "resource_id": "linear_team:SALES",
        "reason": "Seeded grant for Linear issue creation",
        "issuer": "seed",
        "proof_id": "seed_linear_grant",
        "ttl_seconds": 86400,
        "call_count_remaining": 10,
        "expires_at": "2026-06-29T08:23:51",
        "created_at": "2026-06-28T08:23:51"
      }
    ],
    "credential_leases": [],
    "policy_decisions": [],
    "timeline": [
      {
        "event_id": "evt_001",
        "session_id": "sess_demo_001",
        "event_type": "session_started",
        "event_json": "{\"goal_class\": \"sales_renewal_prep\"}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": null,
        "event_hash": "sha256:fef22f6998b1542832923b8f6a9c015d2bf8bd79c62192a86663e3711fdb4619",
        "event_order": 1,
        "payload": {
          "goal_class": "sales_renewal_prep"
        }
      },
      {
        "event_id": "evt_002",
        "session_id": "sess_demo_001",
        "event_type": "historical_trace_seeded",
        "event_json": "{\"departments\": [\"Sales\", \"Support\", \"Finance\", \"Engineering\", \"Customer Success\"], \"recipe_ids\": [\"recipe_sales_renewal_v3\", \"recipe_support_escalation_v2\", \"recipe_finance_vendor_review_v2\", \"recipe_eng_incident_followup_v1\", \"recipe_success_qbr_v1\"]}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": "sha256:fef22f6998b1542832923b8f6a9c015d2bf8bd79c62192a86663e3711fdb4619",
        "event_hash": "sha256:1ce26e5a2b9b35d73bd5b2323e03ac9fee7d63992b0aa69c499752747bbd94e2",
        "event_order": 2,
        "payload": {
          "departments": [
            "Sales",
            "Support",
            "Finance",
            "Engineering",
            "Customer Success"
          ],
          "recipe_ids": [
            "recipe_sales_renewal_v3",
            "recipe_support_escalation_v2",
            "recipe_finance_vendor_review_v2",
            "recipe_eng_incident_followup_v1",
            "recipe_success_qbr_v1"
          ]
        }
      },
      {
        "event_id": "evt_003",
        "session_id": "sess_demo_001",
        "event_type": "credential_binding_seeded",
        "event_json": "{\"credential_ref_ids\": \"[redacted]\", \"injection_mode\": \"gateway_header\", \"provider\": \"1password\", \"secret_exposed_to_agent\": \"[redacted]\", \"tool_ids\": [\"linear.create_issue\", \"slack.search_messages\"]}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": "sha256:1ce26e5a2b9b35d73bd5b2323e03ac9fee7d63992b0aa69c499752747bbd94e2",
        "event_hash": "sha256:218de7ccf388030ae18031bc9692a5ea19fa623350f626c7b6107ed55dab238c",
        "event_order": 3,
        "payload": {
          "credential_ref_ids": "[redacted]",
          "injection_mode": "gateway_header",
          "provider": "1password",
          "secret_exposed_to_agent": "[redacted]",
          "tool_ids": [
            "linear.create_issue",
            "slack.search_messages"
          ]
        }
      },
      {
        "event_id": "evt_1438cc264b92",
        "session_id": "sess_demo_001",
        "event_type": "preflight_requested",
        "event_json": "{\"agent_id\": \"agent_renewal_01\", \"delegation_jwt_verified\": true, \"user_id\": \"user_alice\"}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": "sha256:218de7ccf388030ae18031bc9692a5ea19fa623350f626c7b6107ed55dab238c",
        "event_hash": "sha256:7ff8aa28c4dbd561eeb48074ad5e6b38fba2acdb9a27d984fb6ea4dcd7ec3dec",
        "event_order": 4,
        "payload": {
          "agent_id": "agent_renewal_01",
          "delegation_jwt_verified": true,
          "user_id": "user_alice"
        }
      },
      {
        "event_id": "evt_bfa36a00024c",
        "session_id": "sess_demo_001",
        "event_type": "preflight_completed",
        "event_json": "{\"query_engine\": \"memgraph\", \"recipe_hits\": [\"recipe_sales_renewal_v3\"], \"recipe_retrieval\": \"memgraph\", \"snapshot_id\": \"snap_1c20077da9e8\"}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": "sha256:7ff8aa28c4dbd561eeb48074ad5e6b38fba2acdb9a27d984fb6ea4dcd7ec3dec",
        "event_hash": "sha256:35a29a7f211c5e42cf2e1a4fe0efbc353b31a0a452a2e7ff30833a44e939e58b",
        "event_order": 5,
        "payload": {
          "query_engine": "memgraph",
          "recipe_hits": [
            "recipe_sales_renewal_v3"
          ],
          "recipe_retrieval": "memgraph",
          "snapshot_id": "snap_1c20077da9e8"
        }
      },
      {
        "event_id": "evt_eb1e74b135aa",
        "session_id": "sess_demo_001",
        "event_type": "scope_predicted",
        "event_json": "{\"approval_mode\": \"human_required\", \"confidence\": 0.89, \"prediction_id\": \"pred_188fea7515bd\", \"recipe_id\": \"recipe_sales_renewal_v3\", \"resource_id\": \"slack_channel:sales-acme\", \"scope\": \"slack:channels:history\", \"snapshot_id\": \"snap_1c20077da9e8\", \"tool_id\": \"slack.search_messages\"}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": "sha256:35a29a7f211c5e42cf2e1a4fe0efbc353b31a0a452a2e7ff30833a44e939e58b",
        "event_hash": "sha256:f347a52537f05f09515e0191d85ef58536aea3a1700722859b0e3b73dbaaac32",
        "event_order": 6,
        "payload": {
          "approval_mode": "human_required",
          "confidence": 0.89,
          "prediction_id": "pred_188fea7515bd",
          "recipe_id": "recipe_sales_renewal_v3",
          "resource_id": "slack_channel:sales-acme",
          "scope": "slack:channels:history",
          "snapshot_id": "snap_1c20077da9e8",
          "tool_id": "slack.search_messages"
        }
      },
      {
        "event_id": "evt_216869e61fed",
        "session_id": "sess_demo_001",
        "event_type": "access_request_sent",
        "event_json": "{\"created_before_tool_call\": true, \"prediction_confidence\": 0.89, \"prediction_id\": \"pred_188fea7515bd\", \"proof_id\": \"sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f\", \"recipe_id\": \"recipe_sales_renewal_v3\", \"request_id\": \"req_1c0613c6630b\", \"request_origin\": \"preflight_prediction\", \"resource_id\": \"slack_channel:sales-acme\", \"scope\": \"slack:channels:history\", \"tool_id\": \"slack.search_messages\", \"trigger_phase\": \"preflight\"}",
        "created_at": "2026-06-28T08:23:51",
        "prev_event_hash": "sha256:f347a52537f05f09515e0191d85ef58536aea3a1700722859b0e3b73dbaaac32",
        "event_hash": "sha256:9db5deb685d63d1cd5ca7f2b9cdda495478df7fd4ad08f2bbe6db2680d56d4e3",
        "event_order": 7,
        "payload": {
          "created_before_tool_call": true,
          "prediction_confidence": 0.89,
          "prediction_id": "pred_188fea7515bd",
          "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
          "recipe_id": "recipe_sales_renewal_v3",
          "request_id": "req_1c0613c6630b",
          "request_origin": "preflight_prediction",
          "resource_id": "slack_channel:sales-acme",
          "scope": "slack:channels:history",
          "tool_id": "slack.search_messages",
          "trigger_phase": "preflight"
        }
      }
    ],
    "trace_events": [
      {
        "lane": "Audit",
        "event_type": "session_started",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "goal_class": "sales_renewal_prep"
        },
        "event_hash": "sha256:fef22f6998b1542832923b8f6a9c015d2bf8bd79c62192a86663e3711fdb4619",
        "prev_event_hash": null
      },
      {
        "lane": "Context",
        "event_type": "historical_trace_seeded",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "departments": [
            "Sales",
            "Support",
            "Finance",
            "Engineering",
            "Customer Success"
          ],
          "recipe_ids": [
            "recipe_sales_renewal_v3",
            "recipe_support_escalation_v2",
            "recipe_finance_vendor_review_v2",
            "recipe_eng_incident_followup_v1",
            "recipe_success_qbr_v1"
          ]
        },
        "event_hash": "sha256:1ce26e5a2b9b35d73bd5b2323e03ac9fee7d63992b0aa69c499752747bbd94e2",
        "prev_event_hash": "sha256:fef22f6998b1542832923b8f6a9c015d2bf8bd79c62192a86663e3711fdb4619"
      },
      {
        "lane": "Credential",
        "event_type": "credential_binding_seeded",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "credential_ref_ids": "[redacted]",
          "injection_mode": "gateway_header",
          "provider": "1password",
          "secret_exposed_to_agent": "[redacted]",
          "tool_ids": [
            "linear.create_issue",
            "slack.search_messages"
          ]
        },
        "event_hash": "sha256:218de7ccf388030ae18031bc9692a5ea19fa623350f626c7b6107ed55dab238c",
        "prev_event_hash": "sha256:1ce26e5a2b9b35d73bd5b2323e03ac9fee7d63992b0aa69c499752747bbd94e2"
      },
      {
        "lane": "Context",
        "event_type": "preflight_requested",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "agent_id": "agent_renewal_01",
          "delegation_jwt_verified": true,
          "user_id": "user_alice"
        },
        "event_hash": "sha256:7ff8aa28c4dbd561eeb48074ad5e6b38fba2acdb9a27d984fb6ea4dcd7ec3dec",
        "prev_event_hash": "sha256:218de7ccf388030ae18031bc9692a5ea19fa623350f626c7b6107ed55dab238c"
      },
      {
        "lane": "Context",
        "event_type": "preflight_completed",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "query_engine": "memgraph",
          "recipe_hits": [
            "recipe_sales_renewal_v3"
          ],
          "recipe_retrieval": "memgraph",
          "snapshot_id": "snap_1c20077da9e8"
        },
        "event_hash": "sha256:35a29a7f211c5e42cf2e1a4fe0efbc353b31a0a452a2e7ff30833a44e939e58b",
        "prev_event_hash": "sha256:7ff8aa28c4dbd561eeb48074ad5e6b38fba2acdb9a27d984fb6ea4dcd7ec3dec"
      },
      {
        "lane": "Context",
        "event_type": "scope_predicted",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "approval_mode": "human_required",
          "confidence": 0.89,
          "prediction_id": "pred_188fea7515bd",
          "recipe_id": "recipe_sales_renewal_v3",
          "resource_id": "slack_channel:sales-acme",
          "scope": "slack:channels:history",
          "snapshot_id": "snap_1c20077da9e8",
          "tool_id": "slack.search_messages"
        },
        "event_hash": "sha256:f347a52537f05f09515e0191d85ef58536aea3a1700722859b0e3b73dbaaac32",
        "prev_event_hash": "sha256:35a29a7f211c5e42cf2e1a4fe0efbc353b31a0a452a2e7ff30833a44e939e58b"
      },
      {
        "lane": "Approval",
        "event_type": "access_request_sent",
        "created_at": "2026-06-28T08:23:51",
        "payload": {
          "created_before_tool_call": true,
          "prediction_confidence": 0.89,
          "prediction_id": "pred_188fea7515bd",
          "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
          "recipe_id": "recipe_sales_renewal_v3",
          "request_id": "req_1c0613c6630b",
          "request_origin": "preflight_prediction",
          "resource_id": "slack_channel:sales-acme",
          "scope": "slack:channels:history",
          "tool_id": "slack.search_messages",
          "trigger_phase": "preflight"
        },
        "event_hash": "sha256:9db5deb685d63d1cd5ca7f2b9cdda495478df7fd4ad08f2bbe6db2680d56d4e3",
        "prev_event_hash": "sha256:f347a52537f05f09515e0191d85ef58536aea3a1700722859b0e3b73dbaaac32"
      }
    ],
    "context_graph": {
      "nodes": [
        {
          "node_id": "node_e4cef79723985eca695ebcc9",
          "node_kind": "MCPTool",
          "source_id": "linear.add_comment",
          "label": "linear.add_comment",
          "payload_json": "{\"kind\": \"MCPTool\", \"source_id\": \"linear.add_comment\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "MCPTool",
            "source_id": "linear.add_comment"
          }
        },
        {
          "node_id": "node_256d78d334905ac36f4f0892",
          "node_kind": "MCPTool",
          "source_id": "linear.create_issue",
          "label": "linear.create_issue",
          "payload_json": "{\"kind\": \"MCPTool\", \"source_id\": \"linear.create_issue\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "MCPTool",
            "source_id": "linear.create_issue"
          }
        },
        {
          "node_id": "node_854ca22d75bb0d55aa7da2e2",
          "node_kind": "MCPTool",
          "source_id": "linear.search_issues",
          "label": "linear.search_issues",
          "payload_json": "{\"kind\": \"MCPTool\", \"source_id\": \"linear.search_issues\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "MCPTool",
            "source_id": "linear.search_issues"
          }
        },
        {
          "node_id": "node_921e33a3f7a56ebb13777c9f",
          "node_kind": "MCPTool",
          "source_id": "slack.search_messages",
          "label": "slack.search_messages",
          "payload_json": "{\"kind\": \"MCPTool\", \"source_id\": \"slack.search_messages\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "MCPTool",
            "source_id": "slack.search_messages"
          }
        },
        {
          "node_id": "node_9cba883e6d7e1b807cc17934",
          "node_kind": "Recipe",
          "source_id": "recipe_sales_renewal_v3",
          "label": "Sales Renewal Prep v3",
          "payload_json": "{\"dolt_commit\": \"main\", \"goal_class\": \"sales_renewal_prep\", \"kind\": \"Recipe\", \"predicted_scopes\": [\"linear:comments:create\", \"linear:issues:create\", \"linear:issues:read\", \"slack:channels:history\"], \"predicted_tools\": [\"linear.add_comment\", \"linear.create_issue\", \"linear.search_issues\", \"slack.search_messages\"], \"recipe_id\": \"recipe_sales_renewal_v3\", \"recipe_index_commit\": \"main\", \"score\": 0.89, \"source_id\": \"recipe_sales_renewal_v3\", \"title\": \"Sales Renewal Prep v3\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "dolt_commit": "main",
            "goal_class": "sales_renewal_prep",
            "kind": "Recipe",
            "predicted_scopes": [
              "linear:comments:create",
              "linear:issues:create",
              "linear:issues:read",
              "slack:channels:history"
            ],
            "predicted_tools": [
              "linear.add_comment",
              "linear.create_issue",
              "linear.search_issues",
              "slack.search_messages"
            ],
            "recipe_id": "recipe_sales_renewal_v3",
            "recipe_index_commit": "main",
            "score": 0.89,
            "source_id": "recipe_sales_renewal_v3",
            "title": "Sales Renewal Prep v3"
          }
        },
        {
          "node_id": "node_6229c6a00d47dc728ee867fa",
          "node_kind": "Scope",
          "source_id": "linear:comments:create",
          "label": "linear:comments:create",
          "payload_json": "{\"kind\": \"Scope\", \"source_id\": \"linear:comments:create\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "Scope",
            "source_id": "linear:comments:create"
          }
        },
        {
          "node_id": "node_e6e7de8e91907348d88bcea6",
          "node_kind": "Scope",
          "source_id": "linear:issues:create",
          "label": "linear:issues:create",
          "payload_json": "{\"kind\": \"Scope\", \"source_id\": \"linear:issues:create\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "Scope",
            "source_id": "linear:issues:create"
          }
        },
        {
          "node_id": "node_fec7995ba1b045a7da06af71",
          "node_kind": "Scope",
          "source_id": "linear:issues:read",
          "label": "linear:issues:read",
          "payload_json": "{\"kind\": \"Scope\", \"source_id\": \"linear:issues:read\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "Scope",
            "source_id": "linear:issues:read"
          }
        },
        {
          "node_id": "node_b808a4aaf4e6887c53991baf",
          "node_kind": "Scope",
          "source_id": "slack:channels:history",
          "label": "slack:channels:history",
          "payload_json": "{\"kind\": \"Scope\", \"source_id\": \"slack:channels:history\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "Scope",
            "source_id": "slack:channels:history"
          }
        },
        {
          "node_id": "node_ff454d1380bff2c1a735fa2d",
          "node_kind": "Session",
          "source_id": "sess_demo_001",
          "label": "sess_demo_001",
          "payload_json": "{\"kind\": \"Session\", \"source_id\": \"sess_demo_001\", \"status\": null}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "Session",
            "source_id": "sess_demo_001",
            "status": null
          }
        },
        {
          "node_id": "node_ffac392b3edc2f17bbeb21a2",
          "node_kind": "User",
          "source_id": "user_alice",
          "label": "user_alice",
          "payload_json": "{\"kind\": \"User\", \"source_id\": \"user_alice\"}",
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "User",
            "source_id": "user_alice"
          }
        }
      ],
      "edges": [
        {
          "edge_id": "edge_c0d971240174f042dd9f99ef",
          "src_node_id": "node_ff454d1380bff2c1a735fa2d",
          "dst_node_id": "node_9cba883e6d7e1b807cc17934",
          "edge_kind": "MATCHES",
          "payload_json": "{\"kind\": \"MATCHES\", \"source\": \"graph_context\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "MATCHES",
            "source": "graph_context"
          }
        },
        {
          "edge_id": "edge_14ebb81171f6f1f530f83329",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_b808a4aaf4e6887c53991baf",
          "edge_kind": "PREDICTS_SCOPE",
          "payload_json": "{\"kind\": \"PREDICTS_SCOPE\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_SCOPE"
          }
        },
        {
          "edge_id": "edge_33bd00f7faed21410931a063",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_e6e7de8e91907348d88bcea6",
          "edge_kind": "PREDICTS_SCOPE",
          "payload_json": "{\"kind\": \"PREDICTS_SCOPE\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_SCOPE"
          }
        },
        {
          "edge_id": "edge_a4f9aefa719ae2a87e895076",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_fec7995ba1b045a7da06af71",
          "edge_kind": "PREDICTS_SCOPE",
          "payload_json": "{\"kind\": \"PREDICTS_SCOPE\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_SCOPE"
          }
        },
        {
          "edge_id": "edge_fc6d48efc51217de871a4d9f",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_6229c6a00d47dc728ee867fa",
          "edge_kind": "PREDICTS_SCOPE",
          "payload_json": "{\"kind\": \"PREDICTS_SCOPE\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_SCOPE"
          }
        },
        {
          "edge_id": "edge_1b1fc7e857fe4563527ed2a8",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_921e33a3f7a56ebb13777c9f",
          "edge_kind": "PREDICTS_TOOL",
          "payload_json": "{\"kind\": \"PREDICTS_TOOL\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_TOOL"
          }
        },
        {
          "edge_id": "edge_4bfad58707605f262ee97b2d",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_e4cef79723985eca695ebcc9",
          "edge_kind": "PREDICTS_TOOL",
          "payload_json": "{\"kind\": \"PREDICTS_TOOL\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_TOOL"
          }
        },
        {
          "edge_id": "edge_6fc5f3bd86b5b2c2ad8df7fd",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_854ca22d75bb0d55aa7da2e2",
          "edge_kind": "PREDICTS_TOOL",
          "payload_json": "{\"kind\": \"PREDICTS_TOOL\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_TOOL"
          }
        },
        {
          "edge_id": "edge_75f67ff392dd29bffbb014ae",
          "src_node_id": "node_9cba883e6d7e1b807cc17934",
          "dst_node_id": "node_256d78d334905ac36f4f0892",
          "edge_kind": "PREDICTS_TOOL",
          "payload_json": "{\"kind\": \"PREDICTS_TOOL\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "PREDICTS_TOOL"
          }
        },
        {
          "edge_id": "edge_72e20e42cb8345b1ce9709dd",
          "src_node_id": "node_ffac392b3edc2f17bbeb21a2",
          "dst_node_id": "node_ff454d1380bff2c1a735fa2d",
          "edge_kind": "RUNS",
          "payload_json": "{\"kind\": \"RUNS\"}",
          "confidence": 1,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "RUNS"
          }
        },
        {
          "edge_id": "edge_e493d441bb9606826e4ffb1e",
          "src_node_id": "node_ff454d1380bff2c1a735fa2d",
          "dst_node_id": "node_9cba883e6d7e1b807cc17934",
          "edge_kind": "SIMILAR_RECIPE",
          "payload_json": "{\"kind\": \"SIMILAR_RECIPE\", \"rank\": null, \"source\": \"recipe_retrieval\"}",
          "confidence": 0.89,
          "provenance": "snap_1c20077da9e8",
          "payload": {
            "kind": "SIMILAR_RECIPE",
            "rank": null,
            "source": "recipe_retrieval"
          }
        }
      ]
    },
    "department_traces": [
      {
        "recipe_id": "recipe_sales_renewal_v3",
        "title": "Sales Renewal Prep v3",
        "team_id": "team_sales",
        "team_name": "Sales",
        "goal_class": "sales_renewal_prep",
        "tool_count": 4,
        "scope_count": 4,
        "has_human_gate": 1
      },
      {
        "recipe_id": "recipe_success_qbr_v1",
        "title": "Customer Success QBR Prep v1",
        "team_id": "team_success",
        "team_name": "Customer Success",
        "goal_class": "customer_qbr",
        "tool_count": 2,
        "scope_count": 2,
        "has_human_gate": 1
      },
      {
        "recipe_id": "recipe_eng_incident_followup_v1",
        "title": "Engineering Incident Follow-up v1",
        "team_id": "team_engineering",
        "team_name": "Engineering",
        "goal_class": "incident_followup",
        "tool_count": 3,
        "scope_count": 3,
        "has_human_gate": 1
      },
      {
        "recipe_id": "recipe_finance_vendor_review_v2",
        "title": "Finance Vendor Review v2",
        "team_id": "team_finance",
        "team_name": "Finance",
        "goal_class": "vendor_review",
        "tool_count": 2,
        "scope_count": 2,
        "has_human_gate": 1
      },
      {
        "recipe_id": "recipe_support_escalation_v2",
        "title": "Support Escalation Triage v2",
        "team_id": "team_support",
        "team_name": "Support",
        "goal_class": "support_escalation",
        "tool_count": 3,
        "scope_count": 3,
        "has_human_gate": 1
      }
    ],
    "demo_apps": {
      "linear": {
        "issues": [
          {
            "issue_id": "LIN-demo-renewal",
            "team_id": "linear_team:SALES",
            "title": "Acme renewal baseline",
            "description": "Seed issue showing the demo Linear app before the agent creates follow-up work.",
            "state": "open",
            "priority": "medium",
            "source_session_id": "sess_demo_001",
            "created_by_agent_id": "seed",
            "policy_decision_id": "seed_policy",
            "credential_lease_id": null,
            "created_at": "2026-06-28T08:23:51",
            "updated_at": "2026-06-28T08:23:51"
          }
        ],
        "comments": []
      },
      "slack": {
        "channels": [
          "slack_channel:sales-acme"
        ],
        "messages": [
          {
            "message_id": "msg_sales_acme_001",
            "channel_id": "slack_channel:sales-acme",
            "user_id": "user_alice",
            "user_name": "Alice",
            "text": "Acme renewal discussion: contract ends Q3 and the customer wants pricing detail.",
            "source_session_id": "sess_demo_001",
            "policy_decision_id": "seed_policy",
            "message_kind": "message",
            "is_untrusted": 0,
            "created_at": "2026-06-28T08:23:51"
          },
          {
            "message_id": "msg_sales_acme_002",
            "channel_id": "slack_channel:sales-acme",
            "user_id": "user_bob",
            "user_name": "Bob",
            "text": "Please create a follow-up issue once the renewal summary is ready.",
            "source_session_id": "sess_demo_001",
            "policy_decision_id": "seed_policy",
            "message_kind": "message",
            "is_untrusted": 0,
            "created_at": "2026-06-28T08:23:51"
          },
          {
            "message_id": "msg_sales_acme_003",
            "channel_id": "slack_channel:sales-acme",
            "user_id": "external_note",
            "user_name": "External Note",
            "text": "Untrusted customer-provided text should remain data and must not expand the session goal.",
            "source_session_id": "sess_demo_001",
            "policy_decision_id": "seed_policy",
            "message_kind": "untrusted_context",
            "is_untrusted": 1,
            "created_at": "2026-06-28T08:23:51"
          }
        ]
      }
    },
    "authorization_ledger": [
      {
        "kind": "access_request",
        "status": "pending",
        "tool_id": "slack.search_messages",
        "resource_id": "slack_channel:sales-acme",
        "scope": "slack:channels:history",
        "reason": "Preflight predicted this human-required scope from governed recipe memory (recipe_sales_renewal_v3).",
        "request_id": "req_1c0613c6630b",
        "policy_engine": "",
        "rules": [],
        "created_at": "2026-06-28T08:23:51"
      }
    ],
    "agent_run": {
      "status": "waiting_for_async_approval",
      "current_step": "access_request_sent",
      "pending_approvals": 1,
      "approved_requests": 0,
      "policy_decisions": 0,
      "credential_leases": 0,
      "last_event_hash": "sha256:9db5deb685d63d1cd5ca7f2b9cdda495478df7fd4ad08f2bbe6db2680d56d4e3"
    },
    "recipe_proposals": [],
    "index_status": {
      "indexed_recipes": 0,
      "recipes": []
    },
    "ui_status": "waiting_for_human",
    "mode": "live"
  },
  "identity": {
    "session_id": "sess_demo_001",
    "user_id": "user_alice",
    "team_id": "team_sales",
    "agent_id": "agent_renewal_01",
    "identity_ref": "agentic-iam://uuid-renewal-bot",
    "trust_score": 0.92,
    "agent_status": "active",
    "delegation_present": true,
    "delegation": {
      "session_id": "sess_demo_001",
      "user_id": "user_alice",
      "agent_id": "agent_renewal_01",
      "delegated_at": "2026-06-28T08:23:51"
    },
    "rebac_tuples": [
      "user:user_alice#member@team:team_sales",
      "agent:agent_renewal_01#executes@session:sess_demo_001",
      "agent:agent_renewal_01#identity@agentic-iam://uuid-renewal-bot",
      "user:user_alice#delegates@agent:agent_renewal_01@session:sess_demo_001",
      "session:sess_demo_001#matches@recipe:recipe_sales_renewal_v3"
    ],
    "story": "Agentic-IAM knows who the agent is; ScopeMemory decides what it may do via ReBAC."
  },
  "actionResponses": {
    "reseed": {
      "status": "reseeded",
      "scenario": "hackathon_web_live_trace",
      "synced_rows": 61,
      "graph_engine": "memgraph"
    },
    "preflight": {
      "session_id": "sess_demo_001",
      "agentic_iam": {
        "agent_id": "agent_renewal_01",
        "identity_ref": "agentic-iam://uuid-renewal-bot",
        "trust_score": 0.92,
        "source": "http"
      },
      "delegation_jwt": {
        "verified": true,
        "session_id": "sess_demo_001",
        "user_id": "user_alice",
        "legacy": false
      },
      "agentic_identity": {
        "identity_ref": "agentic-iam://uuid-renewal-bot",
        "trust_score": 0.92,
        "delegation_required": true,
        "delegation_verified": true,
        "iam_source": "http"
      },
      "source_of_truth": "dolt",
      "query_engine": "memgraph",
      "synced_rows": 61,
      "context_snapshot_id": "snap_1c20077da9e8",
      "fact_set_hash": "sha256:57be5f770b32a10d660b3b5b8b943b88d25100c79432a0a5d4aeb3ce89bc1fca",
      "graph_projection": {
        "nodes": 11,
        "edges": 11
      },
      "visible_tools": [
        "auth.explain_denial",
        "auth.preflight_goal",
        "auth.request_scope",
        "auth.show_decision_proof",
        "auth.submit_workflow_feedback",
        "linear.add_comment",
        "linear.create_issue",
        "linear.search_issues",
        "slack.search_messages"
      ],
      "active_grants": [
        {
          "grant_id": "grant_linear_001",
          "session_id": "sess_demo_001",
          "scope": "linear:issues:create",
          "resource_id": "linear_team:SALES",
          "reason": "Seeded grant for Linear issue creation",
          "issuer": "seed",
          "proof_id": "seed_linear_grant",
          "ttl_seconds": 86400,
          "call_count_remaining": 10,
          "expires_at": "2026-06-29T08:23:51",
          "created_at": "2026-06-28T08:23:51"
        }
      ],
      "access_requests": [
        {
          "request_id": "req_1c0613c6630b",
          "session_id": "sess_demo_001",
          "user_id": "user_alice",
          "requested_scope": "slack:channels:history",
          "requested_resource": "slack_channel:sales-acme",
          "requested_tool_id": "slack.search_messages",
          "reason": "Preflight predicted this human-required scope from governed recipe memory (recipe_sales_renewal_v3).",
          "recipe_id": "recipe_sales_renewal_v3",
          "status": "pending",
          "approver_id": null,
          "created_at": "2026-06-28T08:23:51",
          "agent_id": "agent_renewal_01",
          "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
          "approver_type": "human",
          "expires_at": null,
          "request_origin": "preflight_prediction",
          "prediction_id": "pred_188fea7515bd",
          "prediction_confidence": 0.89,
          "source_trace_ids_json": "[\"recipe_sales_renewal_v3\"]",
          "trigger_phase": "preflight",
          "created_before_tool_call": 1,
          "sent_at": "2026-06-28T08:23:51",
          "first_tool_call_at": null
        }
      ],
      "anticipated_access_requests": [
        {
          "request_id": "req_1c0613c6630b",
          "session_id": "sess_demo_001",
          "user_id": "user_alice",
          "agent_id": "agent_renewal_01",
          "requested_scope": "slack:channels:history",
          "requested_resource": "slack_channel:sales-acme",
          "requested_tool_id": "slack.search_messages",
          "reason": "Preflight predicted this human-required scope from governed recipe memory (recipe_sales_renewal_v3).",
          "recipe_id": "recipe_sales_renewal_v3",
          "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
          "request_origin": "preflight_prediction",
          "prediction_id": "pred_188fea7515bd",
          "prediction_confidence": 0.89,
          "source_trace_ids": [
            "recipe_sales_renewal_v3"
          ],
          "trigger_phase": "preflight",
          "created_before_tool_call": true,
          "status": "pending"
        }
      ],
      "pending_access_requests": [
        {
          "request_id": "req_1c0613c6630b",
          "session_id": "sess_demo_001",
          "user_id": "user_alice",
          "requested_scope": "slack:channels:history",
          "requested_resource": "slack_channel:sales-acme",
          "requested_tool_id": "slack.search_messages",
          "reason": "Preflight predicted this human-required scope from governed recipe memory (recipe_sales_renewal_v3).",
          "recipe_id": "recipe_sales_renewal_v3",
          "status": "pending",
          "approver_id": null,
          "created_at": "2026-06-28T08:23:51",
          "agent_id": "agent_renewal_01",
          "proof_id": "sha256:ea15aa26b5cdb1d901f795d45605711f45909621221fea150adeb45ca3c32e9f",
          "approver_type": "human",
          "expires_at": null,
          "request_origin": "preflight_prediction",
          "prediction_id": "pred_188fea7515bd",
          "prediction_confidence": 0.89,
          "source_trace_ids_json": "[\"recipe_sales_renewal_v3\"]",
          "trigger_phase": "preflight",
          "created_before_tool_call": 1,
          "sent_at": "2026-06-28T08:23:51",
          "first_tool_call_at": null
        }
      ],
      "recipe_hits": [
        {
          "recipe_id": "recipe_sales_renewal_v3",
          "title": "Sales Renewal Prep v3",
          "goal_class": "sales_renewal_prep",
          "score": 0.89,
          "dolt_commit": "main",
          "recipe_index_commit": "main",
          "predicted_tools": [
            "linear.add_comment",
            "linear.create_issue",
            "linear.search_issues",
            "slack.search_messages"
          ],
          "predicted_scopes": [
            "linear:comments:create",
            "linear:issues:create",
            "linear:issues:read",
            "slack:channels:history"
          ]
        }
      ],
      "reified_recipe_hits": [
        {
          "session_id": "sess_demo_001",
          "recipe_id": "recipe_sales_renewal_v3",
          "score": 0.89,
          "rank_order": 1,
          "graph_node_id": "node_0c6a93355cde1cba70460d3b",
          "dolt_commit_hash": "main",
          "recipe_index_commit": "main",
          "reified": true
        }
      ],
      "recipe_retrieval": "memgraph",
      "agent": {
        "display_name": "RenewalBot",
        "id": "agent_renewal_01",
        "identity_ref": "agentic-iam://uuid-renewal-bot",
        "status": "active",
        "trust_score": 0.92
      },
      "user_id": "user_alice",
      "goal_class": "sales_renewal_prep",
      "matched_recipe": {
        "goal_class": "sales_renewal_prep",
        "id": "recipe_sales_renewal_v3",
        "status": "accepted",
        "team_id": "team_sales",
        "title": "Sales Renewal Prep v3"
      },
      "predicted_tools": [
        "linear.add_comment",
        "linear.create_issue",
        "linear.search_issues",
        "slack.search_messages"
      ],
      "predicted_scopes": [
        "linear:comments:create",
        "linear:issues:create",
        "linear:issues:read",
        "slack:channels:history"
      ],
      "delegation_present": true,
      "delegation": {
        "session_id": "sess_demo_001",
        "user_id": "user_alice",
        "agent_id": "agent_renewal_01"
      },
      "agent_trust_score": 0.92,
      "identity_ref": "agentic-iam://uuid-renewal-bot",
      "rebac_tuples": [
        "user:user_alice#member@team:team_sales",
        "agent:agent_renewal_01#executes@session:sess_demo_001",
        "agent:agent_renewal_01#identity@agentic-iam://uuid-renewal-bot",
        "user:user_alice#delegates@agent:agent_renewal_01@session:sess_demo_001",
        "session:sess_demo_001#matches@recipe:recipe_sales_renewal_v3"
      ]
    },
    "delegation_token": {
      "delegation_token": "static-demo-token"
    }
  }
};
