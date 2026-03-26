import React, { useState, useEffect, useCallback } from "react";
import { formatCurrency } from "../utils/formatters";

// Modal Component for Popups
const Modal = ({ isOpen, onClose, title, content, icon }) => {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        animation: "fadeIn 0.2s ease",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "linear-gradient(135deg, #0f1420 0%, #141929 100%)",
          borderRadius: "20px",
          maxWidth: "500px",
          width: "90%",
          maxHeight: "80vh",
          overflow: "auto",
          border: "1px solid #2a3450",
          boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
          animation: "slideUp 0.3s ease",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #2a3450",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "24px" }}>{icon}</span>
            <h3 style={{ margin: 0, color: "#e8eaf2" }}>{title}</h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "#1e2a3a",
              border: "none",
              color: "#8899bb",
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ✕
          </button>
        </div>
        <div
          style={{
            padding: "24px",
            whiteSpace: "pre-wrap",
            lineHeight: "1.6",
            color: "#c8d0e8",
          }}
        >
          {content}
        </div>
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid #2a3450",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: "8px 20px",
              background: "linear-gradient(135deg, #4f6ef7, #818cf8)",
              border: "none",
              borderRadius: "8px",
              color: "#fff",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

const FestivalPlanner = ({ financialData }) => {
  const [festivals, setFestivals] = useState([]);
  const [selectedFestival, setSelectedFestival] = useState(null);
  const [planningSteps, setPlanningSteps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionPlan, setActionPlan] = useState(null);
  const [emailDraft, setEmailDraft] = useState("");
  const [modal, setModal] = useState({
    isOpen: false,
    title: "",
    content: "",
    icon: "",
  });

  // PER FESTIVAL completed steps
  const [completedStepsMap, setCompletedStepsMap] = useState(() => {
    try {
      const saved = localStorage.getItem("festivalCompletedStepsMap");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // Persist data
  useEffect(() => {
    localStorage.setItem(
      "festivalCompletedStepsMap",
      JSON.stringify(completedStepsMap),
    );
  }, [completedStepsMap]);

  // Get completed steps for current festival
  const getCurrentFestivalCompletedSteps = () => {
    if (!selectedFestival) return [];
    return completedStepsMap[selectedFestival.name] || [];
  };

  // Mark step as completed for current festival
  const markStepCompleted = (stepId) => {
    if (!selectedFestival) return;
    const currentSteps = completedStepsMap[selectedFestival.name] || [];
    if (!currentSteps.includes(stepId)) {
      setCompletedStepsMap((prev) => ({
        ...prev,
        [selectedFestival.name]: [...currentSteps, stepId],
      }));
    }
  };

  // Check if step is completed for current festival
  const isStepCompleted = (stepId) => {
    if (!selectedFestival) return false;
    const currentSteps = completedStepsMap[selectedFestival.name] || [];
    return currentSteps.includes(stepId);
  };

  // Festival calendar data
  const festivalCalendar = {
    2026: {
      "Makar Sankranti": {
        date: "2026-01-14",
        type: "regional",
        impact: "medium",
        prepDays: 7,
        expenses: ["gifts", "travel"],
        description: "Harvest festival",
        avgSpend: 10000,
      },
      Holi: {
        date: "2026-03-04",
        type: "national",
        impact: "high",
        prepDays: 10,
        expenses: ["colors", "food", "gifts"],
        description: "Festival of colors",
        avgSpend: 15000,
      },
      "Ramzan/Eid": {
        date: "2026-03-30",
        type: "religious",
        impact: "high",
        prepDays: 15,
        expenses: ["gifts", "food", "charity"],
        description: "End of Ramadan",
        avgSpend: 25000,
      },
      "Akshaya Tritiya": {
        date: "2026-04-19",
        type: "religious",
        impact: "medium",
        prepDays: 5,
        expenses: ["gold", "investments"],
        description: "Auspicious for investments",
        avgSpend: 50000,
      },
      "Raksha Bandhan": {
        date: "2026-08-08",
        type: "national",
        impact: "medium",
        prepDays: 7,
        expenses: ["gifts", "travel"],
        description: "Sibling bond festival",
        avgSpend: 8000,
      },
      Janmashtami: {
        date: "2026-08-14",
        type: "national",
        impact: "medium",
        prepDays: 5,
        expenses: ["decorations", "food"],
        description: "Lord Krishna's birthday",
        avgSpend: 10000,
      },
      "Ganesh Chaturthi": {
        date: "2026-09-04",
        type: "national",
        impact: "high",
        prepDays: 15,
        expenses: ["decorations", "offerings", "travel"],
        description: "Ganesha festival",
        avgSpend: 20000,
      },
      "Navratri/Dussehra": {
        date: "2026-10-02",
        type: "national",
        impact: "high",
        prepDays: 15,
        expenses: ["clothing", "gifts", "travel"],
        description: "Nine nights festival",
        avgSpend: 25000,
      },
      Diwali: {
        date: "2026-10-20",
        type: "national",
        impact: "critical",
        prepDays: 30,
        expenses: ["gifts", "bonuses", "decorations", "crackers"],
        description: "Festival of lights",
        avgSpend: 50000,
      },
      "Bhai Dooj": {
        date: "2026-10-22",
        type: "national",
        impact: "medium",
        prepDays: 5,
        expenses: ["gifts"],
        description: "Sibling celebration",
        avgSpend: 5000,
      },
      "Chhath Puja": {
        date: "2026-11-05",
        type: "regional",
        impact: "medium",
        prepDays: 7,
        expenses: ["offerings", "travel"],
        description: "Sun worship festival",
        avgSpend: 15000,
      },
      Christmas: {
        date: "2026-12-25",
        type: "national",
        impact: "medium",
        prepDays: 15,
        expenses: ["gifts", "food", "decorations"],
        description: "Christmas celebration",
        avgSpend: 20000,
      },
    },
  };

  // Detect upcoming festivals
  useEffect(() => {
    detectFestivals();
  }, []);

  const detectFestivals = () => {
    const today = new Date();
    const currentYear = today.getFullYear();
    const festivalsData = festivalCalendar[currentYear] || {};

    const upcoming = [];
    const next180Days = new Date(today);
    next180Days.setDate(today.getDate() + 180);

    for (const [name, details] of Object.entries(festivalsData)) {
      const festivalDate = new Date(details.date);
      if (festivalDate >= today && festivalDate <= next180Days) {
        const daysAway = Math.ceil(
          (festivalDate - today) / (1000 * 60 * 60 * 24),
        );
        upcoming.push({
          name,
          date: details.date,
          daysAway,
          impact: details.impact,
          prepDays: details.prepDays,
          type: details.type,
          expenses: details.expenses,
          description: details.description,
          avgSpend: details.avgSpend,
        });
      }
    }

    setFestivals(upcoming.sort((a, b) => a.daysAway - b.daysAway));

    if (upcoming.length > 0 && !selectedFestival) {
      setSelectedFestival(upcoming[0]);
    }
  };

  // Generate action plan when festival is selected
  useEffect(() => {
    if (selectedFestival) {
      generateActionPlan(selectedFestival);
    }
  }, [selectedFestival]);

  const generateActionPlan = async (festival) => {
    setLoading(true);

    let recommendedReserve = festival.avgSpend;
    let urgencyColor = "";
    let urgencyLevel = "";

    switch (festival.impact) {
      case "critical":
        recommendedReserve = Math.max(recommendedReserve, 50000);
        urgencyColor = "#ff4d6d";
        urgencyLevel = "CRITICAL - Immediate Action Required";
        break;
      case "high":
        recommendedReserve = Math.max(recommendedReserve, 25000);
        urgencyColor = "#f59e0b";
        urgencyLevel = "HIGH - Plan Now";
        break;
      case "medium":
        recommendedReserve = Math.max(recommendedReserve, 15000);
        urgencyColor = "#3b82f6";
        urgencyLevel = "MEDIUM - Start Preparing";
        break;
      default:
        recommendedReserve = Math.max(recommendedReserve, 5000);
        urgencyColor = "#10b981";
        urgencyLevel = "LOW - Monitor";
    }

    const actionSteps = [
      {
        id: 1,
        title: "💰 Budget Planning",
        description: `Recommended budget for ${festival.name}: ${formatCurrency(recommendedReserve)}`,
        deadline: `${festival.prepDays} days before festival`,
        action: "budget_info",
        tip: `Average spending for ${festival.name} is ${formatCurrency(festival.avgSpend)}`,
      },
      {
        id: 2,
        title: "📅 Vendor Payment Schedule",
        description: `Pay critical vendors by ${new Date(new Date(festival.date).setDate(new Date(festival.date).getDate() - 7)).toLocaleDateString()}`,
        deadline: "7 days before festival",
        action: "schedule_payments",
        tip: "Vendors often close during festival week",
      },
      {
        id: 3,
        title: "📥 Accelerate Collections",
        description: "Send reminders to customers for pending payments",
        deadline: "10 days before festival",
        action: "send_reminders",
        tip: "Offer 2-3% discount for early payments",
      },
      {
        id: 4,
        title: "🤝 Negotiate with Vendors",
        description: "Request payment extensions from non-critical vendors",
        deadline: "14 days before festival",
        action: "negotiate",
        tip: "Maintain good relationships for future flexibility",
      },
    ];

    setPlanningSteps(actionSteps);

    const email = `Dear Vendor/Partner,

As ${festival.name} (${festival.date}) approaches, we are reviewing our payment schedule to ensure smooth operations during the festive season.

We plan to clear all outstanding dues by ${new Date(new Date(festival.date).setDate(new Date(festival.date).getDate() - 5)).toLocaleDateString()} to allow for holiday closures.

We value our partnership and appreciate your understanding during this festive period.

Wishing you and your team a wonderful ${festival.name} celebration!

Best regards,
Finance Team
PayWise`;

    setEmailDraft(email);

    setActionPlan({
      festival: festival,
      recommendedReserve: recommendedReserve,
      urgencyColor,
      urgencyLevel,
    });

    setLoading(false);
  };

  const showModal = (title, content, icon = "ℹ️") => {
    setModal({ isOpen: true, title, content, icon });
  };

  const executeAction = async (action, stepId) => {
    // Mark step as completed for THIS SPECIFIC FESTIVAL only
    if (!isStepCompleted(stepId)) {
      markStepCompleted(stepId);
    }

    switch (action) {
      case "budget_info":
        showModal(
          "💰 Festival Budget",
          `Recommended Budget for ${selectedFestival.name}: ${formatCurrency(actionPlan?.recommendedReserve)}\n\n` +
            `This covers:\n` +
            `• Gifts & Celebrations\n` +
            `• Festive Expenses\n` +
            `• Emergency Buffer\n\n` +
            `Plan to set aside this amount ${selectedFestival.prepDays} days before the festival.`,
          "💰",
        );
        break;
      case "schedule_payments":
        showModal(
          "📅 Payment Schedule",
          `Critical Payments for ${selectedFestival.name} (Pay before ${new Date(new Date(selectedFestival.date).setDate(new Date(selectedFestival.date).getDate() - 7)).toLocaleDateString()}):\n\n` +
            `• ${selectedFestival.name} vendors\n` +
            `• Employee festival bonuses\n` +
            `• Gift purchases\n\n` +
            `Payment Methods:\n` +
            `• NEFT/RTGS for large amounts (> ₹50,000)\n` +
            `• UPI for urgent payments\n` +
            `• Schedule payments 3-5 days before festival`,
          "📅",
        );
        break;
      case "send_reminders":
        showModal(
          "📧 Payment Reminder Template",
          `Subject: Payment Reminder - ${selectedFestival.name} Season\n\n` +
            `Dear Customer,\n\n` +
            `As ${selectedFestival.name} approaches on ${selectedFestival.date}, kindly clear pending invoices to help us manage festive season payments.\n\n` +
            `Early payment (by ${new Date(new Date(selectedFestival.date).setDate(new Date(selectedFestival.date).getDate() - 10)).toLocaleDateString()}) qualifies for 2% discount.\n\n` +
            `Thank you for your cooperation!\n\n` +
            `Best regards,\nFinance Team`,
          "📧",
        );
        break;
      case "negotiate":
        showModal(
          "🤝 Negotiation Tips",
          `Vendors to Approach for ${selectedFestival.name}:\n` +
            `• Non-critical suppliers\n` +
            `• Those with good relationship history\n\n` +
            `Suggested Message:\n` +
            `"Due to ${selectedFestival.name} season cash flow, can we extend payment by 15 days? Happy to pay partial amount now."\n\n` +
            `Best approached 2-3 weeks before festival\n` +
            `Keep communication professional and appreciative`,
          "🤝",
        );
        break;
    }
  };

  const copyEmailToClipboard = () => {
    navigator.clipboard.writeText(emailDraft);
    showModal("📋 Success", "Email draft copied to clipboard!", "✓");
  };

  const exportPlan = () => {
    const report = {
      festival: selectedFestival?.name,
      date: selectedFestival?.date,
      daysAway: selectedFestival?.daysAway,
      recommendedBudget: actionPlan?.recommendedReserve,
      completedSteps: getCurrentFestivalCompletedSteps().length,
      totalSteps: planningSteps.length,
      emailDraft: emailDraft,
      generatedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `festival_plan_${selectedFestival?.name}_${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showModal(
      "📄 Export Successful",
      "Festival plan exported successfully!",
      "✓",
    );
  };

  if (festivals.length === 0) {
    return (
      <div
        style={{
          background: "linear-gradient(135deg, #0f1420 0%, #141929 100%)",
          borderRadius: "20px",
          padding: "60px 40px",
          textAlign: "center",
          border: "1px solid #1e2a3a",
        }}
      >
        <div style={{ fontSize: "64px", marginBottom: "20px" }}>🎉</div>
        <h3 style={{ color: "#e8eaf2", marginBottom: "12px" }}>
          No Upcoming Festivals
        </h3>
        <p style={{ color: "#4b5a7a", fontSize: "14px" }}>
          No major festivals detected in the next 180 days.
          <br />
          Relax and plan ahead for future celebrations!
        </p>
      </div>
    );
  }

  const currentCompletedSteps = getCurrentFestivalCompletedSteps();

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { transform: translateY(30px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 3px solid #1e2a3a;
          border-top-color: #4f6ef7;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>

      <Modal
        isOpen={modal.isOpen}
        onClose={() => setModal({ ...modal, isOpen: false })}
        title={modal.title}
        content={modal.content}
        icon={modal.icon}
      />

      <div
        style={{
          background: "linear-gradient(135deg, #0f1420 0%, #141929 100%)",
          borderRadius: "20px",
          overflow: "hidden",
          border: "1px solid #1e2a3a",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            background: "linear-gradient(135deg, #1e1a3a, #0f1420)",
            borderBottom: "1px solid #2a3450",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "8px",
            }}
          >
            <span style={{ fontSize: "32px" }}>🎉</span>
            <h2 style={{ color: "#e8eaf2", margin: 0 }}>
              Festival Financial Planner
            </h2>
          </div>
          <p style={{ color: "#4b5a7a", margin: 0, fontSize: "14px" }}>
            Plan ahead for upcoming festivals. Get recommendations and action
            plans.
          </p>
        </div>

        {/* Festival Selection Tabs */}
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid #1e2a3a",
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            background: "#0a0f1a",
          }}
        >
          {festivals.map((festival) => {
            const festivalCompletedCount = (
              completedStepsMap[festival.name] || []
            ).length;
            const totalSteps = 4;
            return (
              <button
                key={festival.name}
                onClick={() => setSelectedFestival(festival)}
                style={{
                  padding: "8px 20px",
                  borderRadius: "30px",
                  border:
                    selectedFestival?.name === festival.name
                      ? "2px solid"
                      : "1px solid",
                  borderColor:
                    selectedFestival?.name === festival.name
                      ? festival.impact === "critical"
                        ? "#ff4d6d"
                        : festival.impact === "high"
                          ? "#f59e0b"
                          : "#3b82f6"
                      : "#2a3450",
                  background:
                    selectedFestival?.name === festival.name
                      ? festival.impact === "critical"
                        ? "#ff4d6d20"
                        : festival.impact === "high"
                          ? "#f59e0b20"
                          : "#3b82f620"
                      : "transparent",
                  color:
                    selectedFestival?.name === festival.name
                      ? "#e8eaf2"
                      : "#4b5a7a",
                  cursor: "pointer",
                  fontWeight:
                    selectedFestival?.name === festival.name ? 600 : 400,
                  fontSize: "14px",
                  transition: "all 0.2s ease",
                }}
              >
                {festival.name}
                <span
                  style={{
                    marginLeft: "8px",
                    fontSize: "11px",
                    background:
                      festival.impact === "critical"
                        ? "#ff4d6d"
                        : festival.impact === "high"
                          ? "#f59e0b"
                          : festival.impact === "medium"
                            ? "#3b82f6"
                            : "#10b981",
                    padding: "2px 6px",
                    borderRadius: "12px",
                    color: "#fff",
                  }}
                >
                  {festival.daysAway}d
                </span>
                {festivalCompletedCount > 0 && (
                  <span
                    style={{
                      marginLeft: "8px",
                      fontSize: "10px",
                      background: "#4f6ef7",
                      padding: "2px 6px",
                      borderRadius: "12px",
                      color: "#fff",
                    }}
                  >
                    ✓{festivalCompletedCount}/{totalSteps}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {loading ? (
          <div style={{ padding: "60px", textAlign: "center" }}>
            <div className="loading-spinner" style={{ margin: "0 auto" }}></div>
            <p style={{ color: "#4b5a7a", marginTop: "16px" }}>
              Generating your festival action plan...
            </p>
          </div>
        ) : (
          selectedFestival &&
          actionPlan && (
            <div style={{ padding: "24px" }}>
              {/* Festival Alert Banner */}
              <div
                style={{
                  background: `linear-gradient(135deg, ${actionPlan.urgencyColor}20, transparent)`,
                  borderLeft: `4px solid ${actionPlan.urgencyColor}`,
                  padding: "16px 20px",
                  borderRadius: "12px",
                  marginBottom: "24px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: "28px" }}>
                    {selectedFestival.impact === "critical"
                      ? "🚨"
                      : selectedFestival.impact === "high"
                        ? "⚠️"
                        : "📅"}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: "16px",
                        fontWeight: 700,
                        color: actionPlan.urgencyColor,
                        marginBottom: "4px",
                      }}
                    >
                      {actionPlan.urgencyLevel}
                    </div>
                    <div style={{ fontSize: "14px", color: "#8899bb" }}>
                      {selectedFestival.name} - {selectedFestival.date} (
                      {selectedFestival.daysAway} days away)
                    </div>
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#4b5a7a",
                        marginTop: "4px",
                      }}
                    >
                      {selectedFestival.description}
                    </div>
                  </div>
                </div>
              </div>

              {/* Recommended Reserve Card */}
              <div
                style={{
                  background: "#0a0f1a",
                  padding: "20px",
                  borderRadius: "12px",
                  marginBottom: "24px",
                  border: "1px solid #1e2a3a",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "14px",
                    color: "#4b5a7a",
                    marginBottom: "8px",
                  }}
                >
                  💰 Recommended Reserve for {selectedFestival.name}
                </div>
                <div
                  style={{
                    fontSize: "32px",
                    fontWeight: "bold",
                    color: "#00e5a0",
                  }}
                >
                  {formatCurrency(actionPlan.recommendedReserve)}
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#4b5a7a",
                    marginTop: "8px",
                  }}
                >
                  Plan to set aside this amount {selectedFestival.prepDays} days
                  before the festival
                </div>
              </div>

              {/* Action Plan Steps */}
              <div style={{ marginBottom: "24px" }}>
                <h3
                  style={{
                    color: "#e8eaf2",
                    marginBottom: "16px",
                    fontSize: "18px",
                  }}
                >
                  ✅ Action Plan for {selectedFestival.name}
                </h3>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                  }}
                >
                  {planningSteps.map((step) => {
                    const stepCompleted = isStepCompleted(step.id);
                    return (
                      <div
                        key={step.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "16px",
                          background: stepCompleted ? "#10b98110" : "#0a0f1a",
                          padding: "16px",
                          borderRadius: "12px",
                          border: `1px solid ${stepCompleted ? "#10b981" : "#1e2a3a"}`,
                          transition: "all 0.2s ease",
                        }}
                      >
                        <div
                          style={{
                            width: "36px",
                            height: "36px",
                            borderRadius: "50%",
                            background: stepCompleted ? "#10b981" : "#1e2a3a",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#fff",
                            fontWeight: "bold",
                            fontSize: "14px",
                          }}
                        >
                          {stepCompleted ? "✓" : step.id}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div
                            style={{
                              fontWeight: 600,
                              color: "#e8eaf2",
                              marginBottom: "4px",
                            }}
                          >
                            {step.title}
                          </div>
                          <div
                            style={{
                              fontSize: "13px",
                              color: "#4b5a7a",
                              marginBottom: "4px",
                            }}
                          >
                            {step.description}
                          </div>
                          <div
                            style={{
                              fontSize: "11px",
                              color: "#f59e0b",
                              marginBottom: "4px",
                            }}
                          >
                            ⏰ {step.deadline}
                          </div>
                          <div
                            style={{
                              fontSize: "11px",
                              color: "#4b5a7a",
                              fontStyle: "italic",
                            }}
                          >
                            💡 {step.tip}
                          </div>
                        </div>
                        {!stepCompleted && (
                          <button
                            onClick={() => executeAction(step.action, step.id)}
                            style={{
                              padding: "8px 20px",
                              background: `linear-gradient(135deg, #4f6ef7, #818cf8)`,
                              border: "none",
                              borderRadius: "8px",
                              color: "#fff",
                              cursor: "pointer",
                              fontWeight: 600,
                              fontSize: "12px",
                              transition: "all 0.2s ease",
                            }}
                          >
                            Take Action
                          </button>
                        )}
                        {stepCompleted && (
                          <span
                            style={{
                              color: "#10b981",
                              fontSize: "12px",
                              fontWeight: 600,
                            }}
                          >
                            ✓ Completed
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Progress Summary */}
              <div
                style={{
                  background: "#0a0f1a",
                  padding: "16px",
                  borderRadius: "12px",
                  marginBottom: "24px",
                  border: "1px solid #1e2a3a",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <span style={{ fontSize: "13px", color: "#4b5a7a" }}>
                    Preparation Progress for {selectedFestival.name}
                  </span>
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#e8eaf2",
                    }}
                  >
                    {currentCompletedSteps.length}/{planningSteps.length} Steps
                    Completed
                  </span>
                </div>
                <div
                  style={{
                    height: "6px",
                    background: "#1e2a3a",
                    borderRadius: "3px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${(currentCompletedSteps.length / planningSteps.length) * 100}%`,
                      height: "100%",
                      background: "linear-gradient(90deg, #4f6ef7, #00e5a0)",
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
              </div>

              {/* Email Draft Section */}
              <div
                style={{
                  background: "#0a0f1a",
                  borderRadius: "12px",
                  border: "1px solid #f59e0b",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "12px 16px",
                    background: "#f59e0b20",
                    borderBottom: "1px solid #f59e0b",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <span>✉️</span>
                    <span style={{ fontWeight: 600, color: "#f59e0b" }}>
                      Vendor Communication Draft
                    </span>
                  </div>
                  <button
                    onClick={copyEmailToClipboard}
                    style={{
                      padding: "4px 12px",
                      background: "transparent",
                      border: "1px solid #f59e0b",
                      borderRadius: "6px",
                      color: "#f59e0b",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                  >
                    Copy to Clipboard
                  </button>
                </div>
                <div
                  style={{
                    padding: "16px",
                    whiteSpace: "pre-wrap",
                    fontSize: "13px",
                    color: "#c8d0e8",
                    lineHeight: "1.6",
                    fontFamily: "monospace",
                  }}
                >
                  {emailDraft}
                </div>
              </div>

              {/* Export Button */}
              <div
                style={{
                  marginTop: "24px",
                  display: "flex",
                  justifyContent: "flex-end",
                }}
              >
                <button
                  onClick={exportPlan}
                  style={{
                    padding: "10px 24px",
                    background: "linear-gradient(135deg, #4f6ef7, #818cf8)",
                    border: "none",
                    borderRadius: "10px",
                    color: "#fff",
                    cursor: "pointer",
                    fontWeight: 600,
                    fontSize: "14px",
                  }}
                >
                  📄 Export Festival Plan
                </button>
              </div>
            </div>
          )
        )}
      </div>
    </>
  );
};

export default FestivalPlanner;
