"""Classical ML / data science depth pack for the AI SDE bank (Section 4).

The bank already carries from-scratch implementations (see the ML Coding
category) and modern LLM material. What was missing was the CONCEPTUAL depth
an AI/DS student is grilled on: how each classic algorithm actually works,
which one to reach for, how to evaluate it honestly, and what goes wrong in
practice.

House style, following the prompt this pack was built for: intuition first
(a picture you can hold in your head), then the precise technical statement,
then a short worked example with real numbers. Imported by ai_sde_bank.py,
which supplies the Q(...) constructor.
"""


def _c(s):
    return s.strip("\n")


def build(Q):
    entries = []

    # ── Paradigms and the classic algorithms ──────────────────────────────
    entries += [
        Q("ml_concepts", "Supervised vs unsupervised vs semi-supervised vs self-supervised vs reinforcement learning",
          "INTUITION: it comes down to what feedback the model gets. Supervised = a teacher gives you the answer to every question. Unsupervised = no answers at all, just 'find the structure in this'. Semi-supervised = a few answered questions and a mountain of unanswered ones. Self-supervised = you MAKE answers out of the data itself (hide a word and predict it). Reinforcement = no answers, just a score after a sequence of actions. PRECISE VERSION. SUPERVISED learning fits a mapping from features x to a known label y, splitting into classification (discrete y - spam or not) and regression (continuous y - a house price). It needs labels, which are the expensive part; algorithms include linear/logistic regression, trees, SVMs and neural nets. UNSUPERVISED learning finds structure in unlabelled x: clustering (k-means, DBSCAN, hierarchical), dimensionality reduction (PCA, t-SNE, UMAP), density estimation and association rules. Evaluation is the hard part - there is no ground truth, so you use internal measures like the silhouette score plus human judgement. SEMI-SUPERVISED uses a small labelled set plus a large unlabelled one, typically by pseudo-labelling the confident predictions and retraining. SELF-SUPERVISED invents the label from the input: masked language modelling (predict the hidden token), next-token prediction, contrastive learning (two crops of the same image should embed close together). This is the paradigm behind every modern foundation model and is the answer interviewers most want you to name in 2026, because it is how you exploit the internet's worth of unlabelled data. REINFORCEMENT learning has an agent take actions in an environment and receive rewards, optimising a policy for long-run return; it powers game playing, robotics and RLHF for aligning LLMs.",
          ["ml", "supervised", "unsupervised", "self-supervised", "reinforcement", "fundamentals"],
          difficulty="Easy",
          frequency="Very commonly asked - the standard opening ML question at Amazon, Google and every AI/DS interview.",
          mnemonic="Supervised = answers given. Unsupervised = no answers, find structure. Semi = a few answers plus lots of unlabelled. SELF = make your own answers from the data (this is how GPT is trained). RL = no answers, only a reward after acting.",
          example="Same dataset, four framings. Customer transactions: SUPERVISED - predict who churns next month (you have last year's churn labels). UNSUPERVISED - segment customers into groups nobody defined in advance. SELF-SUPERVISED - mask a transaction in a sequence and predict it, learning a general customer embedding you then fine-tune. REINFORCEMENT - choose which offer to show and learn from whether they buy, where the reward arrives after the action and the action changes the next state.",
          code=_c('''
# The same customer data, four ways.
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.semi_supervised import SelfTrainingClassifier

X = np.random.rand(1000, 8)                 # features
y = (X[:, 0] + X[:, 3] > 1.0).astype(int)   # labels (expensive in real life)

# SUPERVISED: labels for every row.
LogisticRegression().fit(X, y)

# UNSUPERVISED: no y at all - just "find 4 groups".
labels = KMeans(n_clusters=4, n_init=10).fit_predict(X)

# SEMI-SUPERVISED: only 50 rows are labelled, -1 means "unknown".
y_partial = np.full(len(y), -1)
y_partial[:50] = y[:50]
SelfTrainingClassifier(LogisticRegression()).fit(X, y_partial)

# SELF-SUPERVISED: the label comes FROM the input. Hide a column, predict it.
mask_col = 3
X_masked = np.delete(X, mask_col, axis=1)   # input  = the other 7 features
y_made_up = X[:, mask_col]                  # target = the hidden one
# Train on that pretext task, throw away the head, keep the learned
# representation, and fine-tune it on your small labelled set. This is
# masked language modelling in miniature.

# REINFORCEMENT (sketch): no dataset, an environment and a reward.
#   for episode in range(N):
#       state = env.reset()
#       while not done:
#           action = policy(state)            # explore vs exploit
#           state, reward, done = env.step(action)
#           policy.update(reward)             # learn from the CONSEQUENCE
'''),
          examples=[
              "One dataset, four framings, so you can hear the difference. Customer transactions, one row per purchase. SUPERVISED: predict who churns next month - you need last year's churn labels, and 'churn' has to be defined precisely (no purchase in 90 days? cancelled subscription?). UNSUPERVISED: segment customers into groups nobody defined in advance - there is no right answer to check against, so you evaluate with a silhouette score and by whether marketing finds the segments actionable. SELF-SUPERVISED: mask a transaction in each customer's sequence and train the model to predict it, producing a general customer embedding you then fine-tune on your small labelled churn set. REINFORCEMENT: choose which offer to show, learn from whether they buy, and accept that today's offer changes tomorrow's state.",
              "Why self-supervised learning changed everything, in one comparison. Labelling a million images costs real money and months - roughly a euro or two per image for careful annotation. But a million UNLABELLED images are free, and if you hide part of each image and train the model to reconstruct it, you have generated a million training signals at zero labelling cost. The model learns edges, textures and object structure from the pretext task, and then a few thousand labelled images are enough to fine-tune it for your actual classification task. That is the entire economics of foundation models: the expensive resource is labels, so invent a task where the data labels itself.",
              "Semi-supervised in practice, and how it goes wrong. You have 500 labelled reviews and 50,000 unlabelled ones. Train on the 500, predict the 50,000, keep only predictions above 0.95 confidence as PSEUDO-LABELS, retrain on the enlarged set, repeat. This genuinely works - but note the failure mode: the model's confident mistakes become training labels, so it reinforces its own bias and the errors compound each round. The guards are a high confidence threshold, a cap on how many pseudo-labels you add per round, and always evaluating on a HUMAN-labelled holdout that never receives pseudo-labels.",
              "Reinforcement learning's distinguishing feature is the DELAY and the FEEDBACK LOOP. In supervised learning the label for each example is fixed and independent. In RL the reward may arrive many actions later (you only learn the chess move was bad twenty moves on - the credit assignment problem), and your action changes what you see next, so the data distribution depends on your own policy. That is why RL needs exploration: if you always take the action you currently believe is best, you never discover a better one. Epsilon-greedy, UCB and Thompson sampling are the standard ways to balance that.",
              "Where an LLM sits, which is the follow-up to expect. All three paradigms appear in one pipeline. PRETRAINING is self-supervised next-token prediction over trillions of tokens - no human labels at all. INSTRUCTION TUNING is supervised fine-tuning on human-written prompt/response pairs, typically tens of thousands of them. RLHF is reinforcement learning where the reward comes from a model trained on human preference comparisons. Being able to name which stage is which is a very common 2026 interview question, and the sequence explains why base models complete text while chat models answer questions.",
              "The practical decision rule when someone hands you a problem. Do you have labels? If yes and they are plentiful, supervised. If you have a few, semi-supervised or transfer learning from a pretrained model - almost never train from scratch. If you have none and want structure, unsupervised. If you have none but can define a pretext task from the data itself, self-supervised pretraining. If there are no labels but there IS a feedback signal from actions taken, reinforcement learning - and be honest that RL in production is far harder than a supervised baseline, so it should be a considered choice rather than a default.",
          ],
          pitfalls="Calling self-supervised learning 'unsupervised' (it uses labels - it just generates them, and that distinction is the whole reason LLMs exist); claiming clustering can be evaluated with accuracy; forgetting that semi-supervised pseudo-labelling amplifies its own mistakes if the confidence threshold is too low.",
          followups="'Where does an LLM fit?' Pretrained self-supervised on next-token prediction, then supervised fine-tuned on instruction pairs, then RLHF - all three paradigms in one pipeline. 'You have a million images and budget to label a thousand - what do you do?' Self-supervised pretraining plus active learning: label the thousand the model is least certain about, not a thousand at random."),

        Q("ml_concepts", "Linear regression from first principles (and its assumptions)",
          "INTUITION: draw the straight line that comes closest to all the points, where 'closest' means the sum of squared vertical distances is as small as possible. Squared, not absolute, for two reasons worth saying: it punishes large errors much harder, and it makes the maths differentiable so there is a clean closed-form solution. PRECISE VERSION: the model is y = w0 + w1x1 + ... + wnxn, fitted by minimising the mean squared error. Two ways to solve it. The NORMAL EQUATION w = (X^T X)^-1 X^T y gives the exact answer in one step, but inverting an n x n matrix is O(n^3) in the number of FEATURES, so it is excellent up to a few thousand features and hopeless beyond. GRADIENT DESCENT iterates w := w - alpha * X^T(Xw - y)/m, is O(n) per step, and is what you use on large or streaming data. Both find the same global optimum because MSE with a linear model is convex - there are no local minima to worry about, which is a genuinely nice property worth stating. THE ASSUMPTIONS, which is what a good interviewer probes: linearity of the relationship, independence of errors (violated by time series), homoscedasticity (constant error variance - if errors fan out with the prediction, your confidence intervals are wrong), normally distributed residuals (needed for inference, not for prediction), and no severe multicollinearity (correlated features make the coefficients unstable and uninterpretable even though predictions stay fine). INTERPRETATION: a coefficient is the expected change in y for a one-unit change in that feature HOLDING THE OTHERS FIXED - and that clause is why correlated features wreck interpretation.",
          ["ml", "linear-regression", "regression", "least-squares", "fundamentals"],
          difficulty="Easy",
          frequency="Very commonly asked - the baseline model every ML interview starts from.",
          mnemonic="Fit the line minimising SQUARED vertical errors. Closed form (X^T X)^-1 X^T y is exact but O(features^3); gradient descent scales. Convex, so one global optimum. Assumptions: LINE - Linearity, Independence, Normal residuals, Equal variance (plus no multicollinearity).",
          code=_c('''
import numpy as np

# ── Closed form: exact, one shot, O(n^3) in the number of features ──────
def fit_normal_equation(X, y):
    X_b = np.c_[np.ones(len(X)), X]                    # prepend the intercept
    # Use pinv, not inv: it survives singular X^T X (perfectly correlated cols)
    return np.linalg.pinv(X_b.T @ X_b) @ X_b.T @ y

# ── Gradient descent: scales to millions of rows ────────────────────────
def fit_gradient_descent(X, y, lr=0.01, epochs=1000):
    X_b = np.c_[np.ones(len(X)), X]
    m, n = X_b.shape
    w = np.zeros(n)
    for _ in range(epochs):
        preds = X_b @ w
        grad = (2 / m) * X_b.T @ (preds - y)           # d/dw of MSE
        w -= lr * grad
    return w

rng = np.random.default_rng(0)
X = rng.random((200, 1)) * 10
y = 3.5 * X[:, 0] + 2.0 + rng.normal(0, 1, 200)        # true w = [2.0, 3.5]

fit_normal_equation(X, y)        # ~[2.0, 3.5]
fit_gradient_descent(X, y)       # ~[2.0, 3.5] - same optimum, iteratively

# ── Diagnostics that matter more than the fit itself ────────────────────
def r_squared(y, y_hat):
    ss_res = ((y - y_hat) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    return 1 - ss_res / ss_tot        # 1.0 = perfect, 0.0 = no better than mean

def vif(X):
    """Variance Inflation Factor: >5-10 means the feature is largely explained
    by the others, so its coefficient is unstable and uninterpretable."""
    out = []
    for j in range(X.shape[1]):
        others = np.delete(X, j, axis=1)
        w = fit_normal_equation(others, X[:, j])
        pred = np.c_[np.ones(len(others)), others] @ w
        out.append(1 / max(1e-12, 1 - r_squared(X[:, j], pred)))
    return out

# Residual plot beats any single number: plot residuals against predictions.
# A random cloud = assumptions hold. A curve = you need a non-linear term.
# A widening cone = heteroscedasticity; try predicting log(y) instead.
'''),
          example="Predicting house price from size and number of rooms. The coefficients come out at 200 per square metre and -15,000 per room, and the negative room coefficient looks absurd - until you notice size and rooms are 0.9 correlated. HOLDING SIZE FIXED, more rooms means smaller rooms, which genuinely is worth less. The model is fine; the naive reading of the coefficient was not. That is multicollinearity in one paragraph.",
          examples=[
              "Fitting a line by hand, so the loss is concrete. Points (1,2), (2,4), (3,5). Guess w=1, b=1: predictions are 2, 3, 4, so errors are 0, 1, 1 and MSE = (0+1+1)/3 = 0.67. Guess w=1.5, b=0.67: predictions 2.17, 3.67, 5.17, errors -0.17, 0.33, -0.17, MSE = 0.06. The second line is better, and least squares finds the best such line exactly - here w=1.5, b=0.667. Doing one iteration of this arithmetic out loud is the fastest way to show you know what 'minimising squared error' actually means.",
              "Why squared rather than absolute error, with the trade named. Squaring makes the loss differentiable everywhere (so gradient descent works and a closed form exists) and it penalises a single error of 10 as much as a hundred errors of 1 - which is right when large errors are disproportionately costly and wrong when they are just outliers. Concretely: on data [10, 12, 11, 13, 200], the constant that minimises MSE is the MEAN, 49.2, and the constant minimising MAE is the MEDIAN, 12. Four of the five points are much better served by 12. Your choice of loss IS a choice about how much outliers should count.",
              "The multicollinearity story, which is the most-asked follow-up. Predicting house price from size and number of rooms gives coefficients of +200 per square metre and -15,000 per room. The negative rooms coefficient looks absurd until you notice size and rooms correlate at 0.9. The coefficient means 'holding SIZE FIXED, one more room' - which means smaller rooms - and that genuinely is worth less. Predictions are unaffected; only the interpretation breaks. Diagnose with a VIF above 5-10, and fix by dropping one feature, combining them (rooms per square metre), or using ridge regression, which stabilises correlated coefficients by shrinking them.",
              "Reading the residual plot, which beats any single metric. Plot residuals (actual minus predicted) against the predicted value. A structureless cloud around zero means the assumptions hold. A U-shape or arch means the true relationship is curved and you need a polynomial or interaction term - the model is systematically wrong in a pattern. A widening cone means heteroscedasticity: the errors grow with the prediction, so your confidence intervals are too narrow at the high end, and the usual fix is to model log(y) instead of y. Ten seconds with this plot finds problems that R-squared hides completely.",
              "R-squared, and the trap in comparing models with it. R-squared is the share of the target's variance the model explains: 0 means no better than always predicting the mean, 1 means perfect. The trap is that it NEVER DECREASES when you add a feature, even a column of random noise - so choosing between a 5-feature and a 50-feature model by R-squared always picks the 50. Use adjusted R-squared, which penalises the feature count, or better, just compare held-out scores. Also note a high R-squared says nothing about causation or about whether the residuals are patterned.",
              "Closed form or gradient descent - how to choose in the room. With 10,000 rows and 50 features, the normal equation inverts a 51x51 matrix, which is instantaneous and exact; use it. With 10 million rows and 100,000 features (text, one-hot encodings), the matrix is 100,000 x 100,000 and inverting it is roughly 10^15 operations - impossible - so gradient descent or its stochastic variant is the only option. The dividing line is the FEATURE count, not the row count, because the inversion cost is O(features^3). Stating that distinction is what the question is testing.",
          ],
          pitfalls="Reading a coefficient as causal; using R-squared to compare models with different feature counts (it never decreases when you add features - use adjusted R-squared or a held-out score); forgetting to scale features before gradient descent, which makes convergence crawl; fitting a straight line to an obviously curved relationship and reporting the R-squared anyway; ignoring outliers, which squared error weights enormously.",
          followups="'When would you use MAE instead of MSE?' When outliers are real data rather than errors - MSE chases them, MAE does not (and Huber loss sits between). 'How do you add regularisation?' Ridge adds lambda times the sum of squared weights (shrinks all), Lasso adds lambda times the sum of absolute weights (drives some to exactly zero, giving feature selection)."),

        Q("ml_concepts", "Logistic regression - why not just use linear regression for classification?",
          "INTUITION: you want a probability, and a straight line does not give you one - it happily predicts 1.4 or -0.3, which is meaningless, and a single far-away point can drag the whole line and flip your decisions. So you squash the line's output through an S-shaped sigmoid, which maps any number to (0,1). The model is still LINEAR in its inputs; only the output is bent, which is why it is called linear regression's classification sibling. PRECISE VERSION: p = sigma(w.x + b) where sigma(z) = 1/(1+e^-z). Training minimises the LOG LOSS (binary cross-entropy) rather than MSE, and the reason is not aesthetic: MSE combined with a sigmoid is NON-CONVEX and gets stuck, while log loss is convex and has a beautifully simple gradient - X^T(p - y)/m, identical in form to linear regression's. Log loss also punishes confident wrong answers enormously (predicting 0.99 for a true 0 costs about 4.6 nats), which is exactly the behaviour you want. THE DECISION BOUNDARY is where w.x + b = 0, a straight line/hyperplane - so logistic regression cannot separate XOR-shaped data without engineered interaction features. INTERPRETATION, which is why the model survives in medicine and credit: a coefficient is the change in the LOG-ODDS per unit of the feature, so exp(w) is an ODDS RATIO - 'each extra year of age multiplies the odds of the disease by 1.05'. That interpretability, plus calibrated probabilities and near-zero inference cost, is why it is still the right first model and the baseline every fancier model must beat.",
          ["ml", "logistic-regression", "classification", "sigmoid", "cross-entropy", "fundamentals"],
          difficulty="Easy",
          frequency="Very commonly asked - the most-asked classical-ML algorithm question at Amazon and Google.",
          mnemonic="Linear regression + sigmoid squash + log loss. MSE with a sigmoid is non-convex, which is the real reason for cross-entropy. Boundary is a straight line. exp(coefficient) = an ODDS RATIO, which is why doctors and lenders still use it.",
          code=_c('''
import numpy as np

def sigmoid(z):
    # Numerically stable: exp of a large positive number overflows.
    return np.where(z >= 0, 1 / (1 + np.exp(-z)),
                    np.exp(z) / (1 + np.exp(z)))

def log_loss(y, p, eps=1e-15):
    p = np.clip(p, eps, 1 - eps)         # never take log(0)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

def fit_logistic(X, y, lr=0.1, epochs=2000, l2=0.0):
    X_b = np.c_[np.ones(len(X)), X]
    w = np.zeros(X_b.shape[1])
    for _ in range(epochs):
        p = sigmoid(X_b @ w)
        # The gradient is the SAME SHAPE as linear regression's - that elegance
        # is exactly what choosing cross-entropy buys you.
        grad = X_b.T @ (p - y) / len(y)
        grad[1:] += l2 * w[1:]           # regularise weights, never the intercept
        w -= lr * grad
    return w

rng = np.random.default_rng(0)
X = rng.normal(size=(500, 2))
y = (X[:, 0] + 0.5 * X[:, 1] > 0).astype(float)
w = fit_logistic(X, y)

# ── Why the loss matters: MSE + sigmoid is non-convex ───────────────────
# With MSE the gradient carries a sigma'(z) factor that VANISHES when the model
# is confidently wrong (z very negative, y = 1): sigma' ~ 0, so the gradient is
# ~0 and learning stalls exactly when it most needs to move.
# With cross-entropy that factor cancels: the gradient is simply (p - y), so a
# confidently wrong prediction produces the LARGEST possible correction.

# ── Interpretation: odds ratios ─────────────────────────────────────────
odds_ratios = np.exp(w[1:])
# odds_ratio 1.05 for "age" => each extra year multiplies the ODDS by 1.05.

# ── Threshold is a BUSINESS decision, not a modelling one ───────────────
def predict(X, w, threshold=0.5):
    return (sigmoid(np.c_[np.ones(len(X)), X] @ w) >= threshold).astype(int)
# Cancer screening: lower the threshold (catch more, accept false alarms).
# Spam filtering: raise it (a lost real email costs more than a seen spam).

# Multi-class: softmax regression (one weight vector per class), or one-vs-rest.
'''),
          example="Predicting loan default. Coefficient for 'debt-to-income ratio' is 0.7, so exp(0.7) = 2.0: each unit increase DOUBLES the odds of default. A regulator can read that sentence and audit it. A gradient-boosted model might score two points better on AUC and cannot be explained that way - which is why lending still runs on logistic regression.",
          examples=[
              "Why a straight line fails at classification, concretely. Fit linear regression to predict 0/1 spam from word count. Most emails have 5-50 spam words and the line fits them fine. Then one email arrives with 500 spam words; least squares tilts the whole line to reduce that point's squared error, and emails that were comfortably classified now fall on the wrong side. One extreme point moved the DECISION BOUNDARY for everyone. Logistic regression is immune because the sigmoid saturates - a point at 500 words is already predicted at 0.999 and pushing it further costs almost nothing.",
              "The sigmoid, computed at a few points, so the shape is real. z = w.x + b, and sigma(z) = 1/(1+e^-z). sigma(-4) = 0.018, sigma(-1) = 0.269, sigma(0) = 0.5, sigma(1) = 0.731, sigma(4) = 0.982. Note the boundary is where z = 0, not where the probability is 0 - and that the curve is steepest at z = 0 (gradient 0.25) and nearly flat beyond |z| = 4. That flatness is exactly the saturation that makes MSE a bad loss here: the gradient it produces vanishes when the model is confidently wrong.",
              "Odds ratios, which is why the model survives in regulated industries. Coefficient 0.7 on debt-to-income ratio means exp(0.7) = 2.01: a one-unit increase DOUBLES the odds of default. Coefficient -0.3 on years-of-employment means exp(-0.3) = 0.74, so each extra year multiplies the odds by 0.74, a 26% reduction. A regulator, a doctor or a credit committee can read those sentences and audit them. A gradient-boosted model might beat this by two points of AUC and cannot produce that sentence, which is why lending and clinical risk scoring still run on logistic regression.",
              "The threshold is a business decision, shown with numbers. A fraud model outputs probabilities. At threshold 0.5: 40 frauds caught, 10 missed, 20 false alarms. At 0.2: 48 caught, 2 missed, 150 false alarms. Which is better depends entirely on the cost ratio. If a missed fraud costs 500 euro and reviewing a false alarm costs 5, then 0.5 costs 10*500 + 20*5 = 5,100 and 0.2 costs 2*500 + 150*5 = 1,750 - so the lower threshold wins clearly. Compute this, do not leave the threshold at 0.5 because that is the default.",
              "Why cross-entropy rather than MSE, stated as the gradient. With cross-entropy the derivative of the loss with respect to the pre-activation z is exactly (p - y). With MSE it is (p - y) * p * (1-p). Consider a confidently wrong prediction: y = 1 and p = 0.01. Cross-entropy gives a gradient of -0.99, the largest correction possible. MSE gives -0.99 * 0.01 * 0.99 = -0.0098, a hundred times smaller - the model learns most slowly exactly when it is most wrong. That is the answer to 'why not MSE?', and it is a real mechanical reason rather than a convention.",
              "What logistic regression cannot do, and the fix. It draws a straight boundary, so on XOR-shaped data (positives at (0,0) and (1,1), negatives at (0,1) and (1,0)) it is stuck at 50% forever no matter how long you train. Adding the interaction feature x1*x2 makes the data linearly separable in the enlarged space and the model solves it instantly. That is the general escape hatch: logistic regression is linear in its FEATURES, not in the raw inputs, so engineered interactions and polynomial terms extend it substantially - which is also the manual version of what a kernel or a hidden layer does automatically.",
          ],
          pitfalls="Using MSE as the loss; forgetting to scale features when regularising (L2 penalises large coefficients, and an unscaled feature gets an artificially small one); reporting accuracy on imbalanced data (99% accuracy by predicting 'no fraud' always); leaving the threshold at 0.5 without thinking about the cost of each error type; expecting it to learn XOR without interaction terms.",
          followups="'How do you extend it to multiple classes?' Softmax (multinomial) regression - one weight vector per class, normalised so the probabilities sum to one. 'Its probabilities are badly calibrated, what now?' Logistic regression is usually well calibrated already; if you regularise heavily or use a different model, apply Platt scaling or isotonic regression on a validation set."),

        Q("ml_concepts", "How a decision tree actually picks a split (Gini, entropy, information gain)",
          "INTUITION: at each node the tree asks 'which single yes/no question about one feature separates the classes best?', tries every feature and every threshold, and keeps the winner. 'Best' means the children are PURER than the parent - closer to being all one class. Repeat until a stopping rule fires. PRECISE VERSION. Purity is measured by GINI IMPURITY, 1 - sum(p_i^2), which is the probability of misclassifying a random element if you labelled it by the node's class distribution, or by ENTROPY, -sum(p_i log2 p_i), which is the bits of uncertainty. Both are 0 for a pure node and maximal for a 50/50 split (0.5 for Gini, 1.0 bit for entropy in the binary case). INFORMATION GAIN is the parent's impurity minus the WEIGHTED AVERAGE of the children's; the tree picks the split maximising it. Gini and entropy agree almost always and Gini is slightly cheaper (no logarithm), which is why it is scikit-learn's default. For REGRESSION trees, the same procedure with variance (MSE) reduction instead of impurity. THE ALGORITHM IS GREEDY - it takes the locally best split and never reconsiders, so it does not find the globally optimal tree (that is NP-hard). THE CHARACTERISTIC WEAKNESS: an unconstrained tree will keep splitting until every leaf is pure, which is perfect memorisation - training accuracy 100%, test accuracy poor. So you constrain it (max_depth, min_samples_leaf, min_impurity_decrease) or prune it afterwards (cost-complexity pruning), and better still you average many trees, which is what random forests exist to do. Also worth naming: information gain is biased toward high-cardinality features, which is why gain RATIO exists and why you should never feed a tree a raw id column.",
          ["ml", "decision-tree", "gini", "entropy", "information-gain", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked - the standard follow-up to 'explain decision trees'.",
          mnemonic="Try every feature and threshold, keep the one whose CHILDREN are purest. Gini = 1 - sum(p^2) (cheap), entropy = -sum(p log p) (bits). Gain = parent impurity minus WEIGHTED child impurity. Greedy, so never globally optimal, and it overfits unless constrained.",
          code=_c('''
import numpy as np

def gini(y):
    if len(y) == 0: return 0.0
    p = np.bincount(y) / len(y)
    return 1.0 - (p ** 2).sum()

def entropy(y):
    if len(y) == 0: return 0.0
    p = np.bincount(y) / len(y)
    p = p[p > 0]                              # 0 log 0 is defined as 0
    return -(p * np.log2(p)).sum()

def information_gain(y, left_idx, right_idx, measure=gini):
    n = len(y)
    yl, yr = y[left_idx], y[right_idx]
    # WEIGHTED average: a split producing one tiny pure child and one huge
    # impure one is not a good split, and the weighting is what says so.
    child = (len(yl) / n) * measure(yl) + (len(yr) / n) * measure(yr)
    return measure(y) - child

def best_split(X, y, measure=gini):
    """Exhaustive search: every feature, every candidate threshold."""
    best = (None, None, -np.inf)
    for feature in range(X.shape[1]):
        values = np.unique(X[:, feature])
        # Candidate thresholds sit BETWEEN consecutive distinct values.
        for thr in (values[:-1] + values[1:]) / 2:
            left = X[:, feature] <= thr
            if left.sum() == 0 or (~left).sum() == 0:
                continue
            gain = information_gain(y, left, ~left, measure)
            if gain > best[2]:
                best = (feature, thr, gain)
    return best            # (feature index, threshold, gain)

# ── Worked numbers ──────────────────────────────────────────────────────
y = np.array([0]*6 + [1]*4)          # 6 negatives, 4 positives
gini(y)       # 1 - (0.6^2 + 0.4^2) = 0.48
entropy(y)    # -(0.6*log2 0.6 + 0.4*log2 0.4) = 0.971 bits

# A split producing [0,0,0,0,0,0] and [1,1,1,1]:
#   children are PURE -> gini 0 and 0 -> weighted child impurity 0
#   gain = 0.48 - 0 = 0.48  (the maximum possible: a perfect split)
#
# A useless split producing [0,0,0,1,1] and [0,0,0,1,1]:
#   each child gini = 1 - (0.6^2+0.4^2) = 0.48 -> weighted = 0.48
#   gain = 0.48 - 0.48 = 0  (learned nothing)

# ── Regression trees: same idea, variance instead of impurity ───────────
def variance_reduction(y, left, right):
    n = len(y)
    return y.var() - (len(y[left])/n) * y[left].var() - (len(y[right])/n) * y[right].var()
'''),
          example="Never give a tree a raw customer_id. Splitting on it produces perfectly pure leaves (one customer each) and enormous information gain, so it wins every split - and the tree has learned a lookup table that generalises to nobody. This bias toward high-cardinality features is the reason gain RATIO (normalising by the split's own entropy) was invented.",
          pitfalls="Forgetting the WEIGHTED average in the gain formula; letting the tree grow unconstrained and then being surprised by 100% training accuracy; treating tree feature-importance as causal (it is split-count and impurity-based, and correlated features split the credit arbitrarily between them); one-hot encoding a high-cardinality categorical, which makes every split a weak binary question.",
          followups="'Gini or entropy - does it matter?' Almost never; they agree on the chosen split in the vast majority of cases and Gini is cheaper. 'How do you stop it overfitting?' Pre-pruning (max_depth, min_samples_leaf), post-pruning (cost-complexity with a validation set), or - far better - bag many trees into a random forest."),

        Q("ml_concepts", "SVM and the kernel trick, explained without the maths",
          "INTUITION: many lines can separate two classes; the SVM picks the one with the widest possible 'street' between them. The width is the MARGIN, the points touching the kerb are the SUPPORT VECTORS, and they alone define the boundary - move any other point and nothing changes, which is a genuinely unusual and useful property. A wide margin is a bet on generalisation: a boundary that keeps its distance from both classes is less likely to be wrong on new points. PRECISE VERSION: maximise the margin 2/||w|| subject to every point being on the correct side, equivalently minimise ||w||^2/2. Real data is not separable, so the SOFT MARGIN adds slack variables and a penalty C: small C means a wide margin and tolerated mistakes (more regularised, more bias), large C means a narrow margin that insists on getting training points right (more variance). C is the single most important hyperparameter. THE KERNEL TRICK is the beautiful part: the optimisation only ever uses DOT PRODUCTS between pairs of points, so you can replace the dot product with a kernel function K(a,b) that equals the dot product in some much higher-dimensional space - without ever computing coordinates in that space. An RBF kernel corresponds to an infinite-dimensional space, and it costs one exponential per pair. So data that is a circle inside a ring, unseparable by any straight line in 2D, becomes linearly separable once lifted. WHEN TO USE ONE: small-to-medium datasets with many features (text classification was its classic home), where the boundary is complex but you cannot afford a neural network's data appetite. It scales badly - roughly O(n^2) to O(n^3) in the number of samples - so above about a hundred thousand rows you use a linear SVM with SGD or something else entirely.",
          ["ml", "svm", "kernel", "margin", "classification", "fundamentals"],
          difficulty="Medium",
          frequency="Commonly asked in ML interviews; the kernel trick is a favourite depth probe.",
          mnemonic="Widest street between the classes; only the SUPPORT VECTORS (points on the kerb) matter. C = how much you tolerate mistakes (small C = wide street, more bias). Kernel trick = the maths only needs DOT PRODUCTS, so swap in a kernel and get a high-dimensional space for free.",
          code=_c('''
import numpy as np
from sklearn.svm import SVC
from sklearn.datasets import make_circles
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# Concentric circles: NO straight line can separate these in 2D.
X, y = make_circles(n_samples=400, factor=0.4, noise=0.08, random_state=0)

linear = make_pipeline(StandardScaler(), SVC(kernel="linear")).fit(X, y)
rbf    = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=1, gamma="scale")).fit(X, y)
linear.score(X, y)      # ~0.5 - a coin flip, as expected
rbf.score(X, y)         # ~0.99 - the same data, lifted into a space where a
                        #         flat boundary exists

# ── Why the trick works, in three lines ─────────────────────────────────
# The trained model only ever needs inner products between points. So define
#     K(a, b) = phi(a) . phi(b)
# and you never have to compute phi() itself. Example - the quadratic kernel
# K(a,b) = (a.b)^2 for 2-D inputs corresponds EXACTLY to
#     phi(x) = [x1^2, sqrt(2) x1 x2, x2^2]        (a 3-D space)
def quadratic_kernel(a, b):
    return (a @ b) ** 2

def explicit_phi(x):
    return np.array([x[0]**2, np.sqrt(2) * x[0] * x[1], x[1]**2])

a, b = np.array([1.0, 2.0]), np.array([3.0, 4.0])
quadratic_kernel(a, b), explicit_phi(a) @ explicit_phi(b)     # identical: 121.0
# For the RBF kernel the equivalent phi is INFINITE-dimensional - and still
# costs one exp() per pair. That is the whole point.

# ── The two hyperparameters, and what they trade ────────────────────────
#   C     : misclassification penalty. Low C  -> wide margin, underfit-ish.
#                                      High C -> narrow margin, overfit-ish.
#   gamma : RBF reach. Low gamma  -> each point influences far away (smooth).
#                      High gamma -> influence is local (wiggly, overfits).
from sklearn.model_selection import GridSearchCV
grid = GridSearchCV(SVC(),
                    {"C": [0.1, 1, 10, 100], "gamma": [0.001, 0.01, 0.1, 1]},
                    cv=5).fit(StandardScaler().fit_transform(X), y)

# SCALING IS NOT OPTIONAL: the RBF kernel is a distance, so a feature measured
# in thousands drowns out one measured in units. Always put a scaler in front.
'''),
          example="Concentric circles: the inner class at radius ~0.4 and the outer at ~1.0. No line separates them. Add a third coordinate z = x^2 + y^2 and the inner class sits low, the outer sits high, and a flat plane cuts cleanly between - that is literally what the kernel does, without ever materialising z. Say that picture in an interview and the trick lands.",
          pitfalls="Not scaling features (the single most common SVM mistake); using an RBF kernel with default gamma on unscaled data and concluding SVMs are bad; running one on a million rows and waiting forever - use LinearSVC or SGDClassifier there; expecting probability outputs (SVMs give distances, and probabilities require an extra Platt calibration step that costs a cross-validation).",
          followups="'Why is it called a SUPPORT vector machine?' Only the points on the margin support the boundary; deleting every other training point gives the identical model, which also means the model is compact. 'SVM or logistic regression?' Logistic when you need calibrated probabilities and interpretability; SVM when the boundary is complex, the data is small-to-medium and you only need the decision."),

        Q("ml_concepts", "k-means clustering: how it works, how to pick k, and where it fails",
          "INTUITION: drop k pins on the map at random, assign every point to its nearest pin, move each pin to the centre of the points it claimed, and repeat until the pins stop moving. That is the whole algorithm - Lloyd's algorithm - and it is why k-means is the first clustering method anyone learns. PRECISE VERSION: it minimises WCSS (within-cluster sum of squares, also called inertia) - the total squared distance from every point to its assigned centroid. Each iteration is guaranteed to reduce WCSS, so it always converges, but only to a LOCAL minimum that depends on the initialisation; hence n_init (run it ten times, keep the best) and k-means++ initialisation, which spreads the initial centroids by choosing each new one with probability proportional to its squared distance from the nearest existing one. Complexity is O(n * k * d * iterations) - linear in the data, which is why it scales when almost nothing else does. CHOOSING K, since the algorithm cannot: the ELBOW METHOD plots WCSS against k and looks for the bend (WCSS always decreases, so the bend and not the minimum is the signal); the SILHOUETTE SCORE, between -1 and 1, measures how much closer a point is to its own cluster than to the nearest other one and can simply be maximised; and often the honest answer is that k comes from the business ('we want three customer tiers'). WHERE IT FAILS, and this is what interviewers want: it assumes clusters are ROUGHLY SPHERICAL, SIMILARLY SIZED and SIMILARLY DENSE, because Euclidean distance to a centroid is the only thing it knows. Elongated, nested or crescent-shaped clusters break it, as do outliers (they drag centroids), and unscaled features let one big-numbered column define every cluster. For those, DBSCAN (density-based, finds arbitrary shapes and labels outliers as noise, needs no k) or Gaussian mixtures (soft assignment, elliptical clusters) are the alternatives to name.",
          ["ml", "k-means", "clustering", "unsupervised", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked - the standard unsupervised-learning question.",
          mnemonic="Assign to nearest centroid, move centroid to the mean, repeat. Minimises WCSS, converges to a LOCAL optimum (so k-means++ and n_init). Pick k with the elbow or silhouette. Assumes round, equal-sized, equal-density clusters - and always scale first.",
          code=_c('''
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

def kmeans_from_scratch(X, k, iters=100, seed=0):
    rng = np.random.default_rng(seed)
    # k-means++ init: spread the seeds out instead of picking at random.
    centroids = [X[rng.integers(len(X))]]
    for _ in range(k - 1):
        d2 = np.min(((X[:, None] - np.array(centroids)) ** 2).sum(-1), axis=1)
        probs = d2 / d2.sum()                     # far points are likelier
        centroids.append(X[rng.choice(len(X), p=probs)])
    centroids = np.array(centroids)

    for _ in range(iters):
        # 1. ASSIGN each point to the nearest centroid
        labels = np.argmin(((X[:, None] - centroids) ** 2).sum(-1), axis=1)
        # 2. MOVE each centroid to the mean of its members
        new = np.array([X[labels == j].mean(axis=0) if (labels == j).any()
                        else centroids[j] for j in range(k)])
        if np.allclose(new, centroids):
            break                                  # converged
        centroids = new
    wcss = sum(((X[labels == j] - centroids[j]) ** 2).sum() for j in range(k))
    return labels, centroids, wcss

# ── Choosing k ──────────────────────────────────────────────────────────
X = StandardScaler().fit_transform(np.random.default_rng(0).random((500, 4)))

inertias, silhouettes = [], []
for k in range(2, 11):
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    inertias.append(km.inertia_)                       # always DECREASES with k
    silhouettes.append(silhouette_score(X, km.labels_))# can be MAXIMISED
# Elbow: plot inertias and find the bend. Silhouette: take the argmax.
best_k = range(2, 11)[int(np.argmax(silhouettes))]

# ── Where k-means fails, and what to use instead ────────────────────────
from sklearn.datasets import make_moons
Xm, _ = make_moons(n_samples=400, noise=0.05)
KMeans(n_clusters=2, n_init=10).fit_predict(Xm)   # slices the crescents in half
DBSCAN(eps=0.2, min_samples=5).fit_predict(Xm)    # recovers both crescents,
                                                  # and labels outliers as -1

# ALWAYS SCALE. Income in euros (0-200,000) and age in years (0-100): without
# scaling, every cluster is defined by income and age is invisible.
'''),
          example="Elbow in numbers: inertia for k = 1..6 comes out 1000, 400, 180, 160, 150, 145. The big drops stop after k = 3 - going from 3 to 4 buys only 20 - so the elbow is 3. Note inertia keeps falling all the way to k = n (where it is exactly 0, one cluster per point), which is precisely why you look for the bend rather than the minimum.",
          pitfalls="Not scaling features; picking k by minimising inertia (it is minimised at k = n); one run without n_init, so a bad initialisation gives a bad answer silently; using it on categorical data (means are meaningless - use k-modes or a different distance); assuming clusters are real just because the algorithm returned some - it always returns k clusters, even on uniform noise.",
          followups="'How does DBSCAN differ?' Density-based: it needs eps and min_samples rather than k, finds arbitrarily shaped clusters, and explicitly marks outliers as noise - but it struggles when clusters have very different densities. 'How do you cluster a million points?' MiniBatchKMeans, or reduce dimensions with PCA first - k-means degrades in high dimensions because Euclidean distances concentrate."),

        Q("ml_concepts", "k-Nearest Neighbours - the model that does no training at all",
          "INTUITION: to classify a new point, look at the k closest training examples and take a vote. Nothing is learned in advance; the training set IS the model. That makes it a LAZY learner - training is O(1) (just store the data) and prediction is expensive, which is the exact opposite of every other algorithm and the reason it gets asked about. PRECISE VERSION: prediction requires computing the distance to every training point, so naive inference is O(n*d) per query; a k-d tree or ball tree reduces that to about O(log n) in low dimensions, and above roughly 20 dimensions those structures degrade to brute force, which is where approximate nearest-neighbour indexes (HNSW, IVF, and the vector databases behind RAG) take over. THE HYPERPARAMETERS: k controls the bias-variance trade directly - k=1 has zero training error and enormous variance (it memorises noise), while a large k over-smooths and eventually predicts the majority class everywhere; use an odd k for binary problems to avoid ties, and choose it by cross-validation. Distance-weighted voting (weight each neighbour by 1/distance) usually beats a plain vote. FEATURE SCALING IS MANDATORY, more so than for any other algorithm, because distance is literally the model - a salary column in the tens of thousands makes an age column invisible. THE CURSE OF DIMENSIONALITY hits kNN hardest: as dimensions grow, all pairwise distances converge toward each other, so 'nearest' stops meaning anything - the practical fix is dimensionality reduction or a learned embedding. WHERE IT SHINES: as a strong baseline, for recommendation ('users like you'), for anomaly detection (distance to the kth neighbour), and conceptually as the retrieval half of every RAG system - semantic search is kNN over embeddings.",
          ["ml", "knn", "classification", "distance", "curse-of-dimensionality", "fundamentals"],
          difficulty="Easy",
          frequency="Commonly asked as a warm-up ML question, and doubly relevant because vector search is kNN.",
          mnemonic="No training - store everything, vote among the k nearest at query time. k small = jagged/overfit, k large = smooth/underfit. SCALE FIRST, distance is the whole model. Above ~20 dimensions, 'nearest' loses meaning - this is the retrieval step in RAG.",
          code=_c('''
import numpy as np
from collections import Counter

def knn_predict(X_train, y_train, x, k=5, weighted=True):
    # Distance to EVERY training point - the cost of laziness.
    d = np.sqrt(((X_train - x) ** 2).sum(axis=1))
    idx = np.argpartition(d, k)[:k]              # O(n), cheaper than a full sort
    if not weighted:
        return Counter(y_train[idx]).most_common(1)[0][0]
    # Distance weighting: nearer neighbours get a bigger vote.
    votes = {}
    for i in idx:
        votes[y_train[i]] = votes.get(y_train[i], 0) + 1 / (d[i] + 1e-9)
    return max(votes, key=votes.get)

# ── Choosing k by cross-validation, and what it trades ──────────────────
# k = 1   : training error 0, and one mislabelled point creates its own island
# k = 5   : usually a good starting point
# k = n   : every prediction is the majority class - maximal bias
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def choose_k(X, y, ks=(1, 3, 5, 11, 25, 51)):
    return {k: cross_val_score(
                make_pipeline(StandardScaler(), KNeighborsClassifier(k)),
                X, y, cv=5).mean()
            for k in ks}

# ── Why scaling is not optional ─────────────────────────────────────────
# Point A: (age 25, salary 50_000)   Point B: (age 60, salary 50_500)
# Unscaled distance = sqrt(35^2 + 500^2) = 501  -> dominated ENTIRELY by salary
# After standardising both to mean 0 / sd 1, the 35-year age gap dominates,
# which is almost certainly what you meant.

# ── The curse of dimensionality, measured ───────────────────────────────
rng = np.random.default_rng(0)
for d in (2, 10, 100, 1000):
    X = rng.random((1000, d))
    dists = np.sqrt(((X[0] - X[1:]) ** 2).sum(1))
    print(d, round(dists.min(), 3), round(dists.max(), 3),
          round(dists.min() / dists.max(), 3))
# The min/max ratio climbs toward 1: in 1000 dimensions the nearest and
# farthest points are nearly equidistant, so "nearest neighbour" is noise.

# ── The same algorithm, at production scale ─────────────────────────────
# Semantic search / RAG retrieval IS kNN over embeddings, with an approximate
# index (HNSW) instead of a brute-force scan - trading exactness for the
# millisecond latency a query needs over millions of vectors.
'''),
          example="A recommendation baseline: embed each user by their ratings, and recommend what the 20 nearest users liked. It needs no training, is easy to explain to a product manager, and is often within a few percent of a far more complex model - which is why 'what does a kNN baseline score?' is a genuinely good question to ask early in any ML project.",
          pitfalls="Not scaling; using it on high-dimensional raw data instead of embeddings; forgetting that inference cost grows with the training set, so a model that is fast in a notebook is slow in production; ties on an even k; treating the training set as disposable - here it must be shipped and kept in memory.",
          followups="'How would you make it fast for a million vectors?' An approximate index: HNSW graphs or IVF with product quantisation, trading a little recall for orders of magnitude in speed. 'Can kNN do regression?' Yes - average the neighbours' values instead of voting, optionally distance-weighted."),

        Q("ml_concepts", "Naive Bayes - why 'naive' and why it works anyway",
          "INTUITION: use Bayes' theorem to ask 'given these words, which class is most likely?', and make one wildly false simplifying assumption - that every feature is INDEPENDENT of the others given the class. 'Free' and 'money' are obviously not independent in spam, but pretending they are turns an intractable joint probability into a simple product of individual ones, and the resulting classifier works surprisingly well. PRECISE VERSION: P(class | features) is proportional to P(class) * product over i of P(feature_i | class). You compute those from counts on the training set and take the argmax; there is no iterative optimisation at all, so training is ONE PASS over the data - which is why it remains the fastest reasonable text classifier in existence and a great baseline. THREE DETAILS THAT GET ASKED. (1) LAPLACE (add-one) SMOOTHING is mandatory: a word never seen with a class gives P = 0, and one zero annihilates the entire product regardless of the other evidence. Add one to every count. (2) Work in LOG SPACE - multiplying hundreds of small probabilities underflows to zero in floating point, so sum the logs instead. (3) VARIANTS matter: Multinomial for word counts, Bernoulli for binary presence/absence, Gaussian for continuous features (assuming each is normally distributed within a class). WHY IT WORKS DESPITE THE FALSE ASSUMPTION: classification only needs the correct ARGMAX, not correct probabilities. The independence assumption distorts the magnitudes badly - Naive Bayes is notoriously overconfident, spitting out 0.9999 - but it frequently leaves the ranking intact. Say that clearly: use it for the decision, do not trust its probabilities, and calibrate if you need them.",
          ["ml", "naive-bayes", "classification", "probability", "nlp", "fundamentals"],
          difficulty="Easy",
          frequency="Commonly asked - the classic 'explain a probabilistic classifier' question, and a favourite for spam-filter examples.",
          mnemonic="Bayes + a pretend independence assumption = a product of simple counts. One pass to train. ALWAYS add-one smooth (a zero kills the product) and ALWAYS work in logs (underflow). Great decisions, terrible calibration.",
          code=_c('''
import numpy as np
from collections import defaultdict, Counter

class MultinomialNaiveBayes:
    """Trains in one pass over the data - no gradients, no iterations."""
    def __init__(self, alpha=1.0):
        self.alpha = alpha                 # Laplace smoothing strength

    def fit(self, docs, labels):
        self.classes = sorted(set(labels))
        self.vocab = {w for d in docs for w in d}
        self.log_prior = {}
        self.log_likelihood = {}
        for c in self.classes:
            class_docs = [d for d, y in zip(docs, labels) if y == c]
            self.log_prior[c] = np.log(len(class_docs) / len(docs))
            counts = Counter(w for d in class_docs for w in d)
            total = sum(counts.values()) + self.alpha * len(self.vocab)
            # SMOOTHING: every vocabulary word gets at least alpha, so no zeros.
            self.log_likelihood[c] = {
                w: np.log((counts[w] + self.alpha) / total) for w in self.vocab
            }
            self._unseen = {c: np.log(self.alpha / total) for c in self.classes}
        return self

    def predict(self, doc):
        scores = {}
        for c in self.classes:
            # LOG SPACE: sum logs instead of multiplying probabilities, or a
            # 200-word document underflows to exactly 0.0 for every class.
            s = self.log_prior[c]
            for w in doc:
                s += self.log_likelihood[c].get(w, self._unseen[c])
            scores[c] = s
        return max(scores, key=scores.get), scores

docs = [["free", "money", "now"], ["free", "offer"], ["meeting", "tomorrow"],
        ["project", "meeting", "notes"]]
labels = ["spam", "spam", "ham", "ham"]
nb = MultinomialNaiveBayes().fit(docs, labels)
nb.predict(["free", "meeting"])       # a genuinely mixed document

# ── Why smoothing is not optional ───────────────────────────────────────
# Without it, a test document containing one word never seen in "ham" gets
# P(ham | doc) = ... * 0 * ... = 0, no matter how ham-like everything else is.
# One unseen word vetoes an entire class. Add-one prevents that veto.

# ── The independence assumption, made concrete ──────────────────────────
# "New York" is treated as two independent tokens, so a document about "new
# jobs in York" scores like one about New York. Bigram features patch the worst
# cases; the model remains blind to interaction in general - and still usually
# lands on the right ARGMAX, which is all a classifier needs.
'''),
          example="Spam filtering with counts: P(spam) = 0.4, P('free'|spam) = 0.1, P('free'|ham) = 0.001. That one word multiplies the spam-versus-ham odds by 100. Add 'money' with a similar ratio and the posterior is effectively 1.0 - which is right as a DECISION and absurd as a PROBABILITY. That gap is the model's signature.",
          pitfalls="Forgetting smoothing; multiplying raw probabilities instead of summing logs; using Gaussian Naive Bayes on features that are clearly not normal; trusting the output probability for thresholding or expected-value calculations; using it where feature interactions carry the signal (it is structurally blind to them).",
          followups="'Why is it still used when better models exist?' Milliseconds to train on millions of documents, trivial to update incrementally, no hyperparameters to speak of, and a strong baseline - if your deep model cannot beat it, something is wrong. 'How do you fix the calibration?' Fit a Platt scaling or isotonic regression on a held-out set."),

        Q("ml_concepts", "PCA - what it does, what it does not, and when to use it",
          "INTUITION: your data is a cloud of points in many dimensions. PCA finds the direction in which the cloud is most stretched out and calls it the first principal component, then the most-stretched direction PERPENDICULAR to that as the second, and so on. Keep the first few and you have a lower-dimensional summary that preserves most of the spread. It is a rotation of the axes to align them with the data's natural spread, followed by dropping the boring axes. PRECISE VERSION: PCA finds the eigenvectors of the covariance matrix (equivalently the right singular vectors of the centred data matrix), ordered by eigenvalue. Each eigenvalue is the VARIANCE EXPLAINED along that component, and you choose how many to keep from the cumulative explained-variance curve - typically enough for 90-95%. Compute it with SVD rather than by forming the covariance matrix explicitly, which is more numerically stable. THREE NON-NEGOTIABLES. (1) CENTRE the data, and STANDARDISE if features are on different scales, because PCA maximises variance and a feature measured in thousands trivially wins. (2) It is UNSUPERVISED - it knows nothing about your labels, so the direction of greatest variance may carry no class information at all; if you want a supervised projection, that is LDA. (3) It is LINEAR - it cannot unroll a swiss roll; kernel PCA, t-SNE or UMAP handle curved structure, and of those t-SNE and UMAP are for VISUALISATION only, since they do not give you a reusable transform and their distances between clusters are not meaningful. WHERE IT EARNS ITS KEEP: compressing correlated features, removing multicollinearity before a linear model, speeding up kNN or k-means, denoising (small components are often noise), and visualising in two dimensions. THE COST: components are linear combinations of every original feature, so interpretability is gone - 'PC1' has no business meaning, which is often a dealbreaker.",
          ["ml", "pca", "dimensionality-reduction", "unsupervised", "svd", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked in ML and data-science interviews.",
          mnemonic="Rotate the axes to line up with the directions of greatest SPREAD, keep the top few. Eigenvalue = variance explained. Must centre and usually standardise. UNSUPERVISED (ignores y) and LINEAR (cannot unroll curves). You lose interpretability.",
          code=_c('''
import numpy as np

def pca(X, n_components=None):
    # 1. CENTRE - PCA is about variance around the mean, so this is required.
    X_centred = X - X.mean(axis=0)
    # 2. SVD is the numerically stable route (avoids forming X^T X).
    U, S, Vt = np.linalg.svd(X_centred, full_matrices=False)
    # 3. Variance explained by each component.
    explained = (S ** 2) / (len(X) - 1)
    ratio = explained / explained.sum()
    k = n_components or len(S)
    return X_centred @ Vt[:k].T, Vt[:k], ratio[:k]

rng = np.random.default_rng(0)
base = rng.normal(size=(500, 2))
X = np.c_[base, base @ [[0.9], [0.4]] + rng.normal(0, 0.05, (500, 1))]  # 3rd col
                                                    # is nearly a copy of 1&2
proj, comps, ratio = pca(X, 2)
ratio.sum()          # ~0.99 - two components capture nearly everything,
                     # because the third dimension carried no new information.

def choose_components(X, target=0.95):
    _, _, ratio = pca(X)
    cum = np.cumsum(ratio)
    return int(np.searchsorted(cum, target) + 1)     # smallest k reaching target

# ── The scaling trap, in numbers ────────────────────────────────────────
# Features: salary (~50,000, sd 20,000) and age (~40, sd 10).
# WITHOUT standardising, salary's variance is 4,000,000 times age's, so PC1 is
# essentially "salary" and age is invisible. Standardise first unless the units
# are genuinely comparable (e.g. all pixel intensities).
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import make_pipeline
pipe = make_pipeline(StandardScaler(), PCA(n_components=0.95))  # keep 95%

# ── PCA is UNSUPERVISED - the failure case to remember ──────────────────
# Two classes separated along a low-variance direction, with a big irrelevant
# variance elsewhere: PC1 captures the irrelevant spread and the classes become
# LESS separable after "reducing" the data. Use LDA when you have labels and
# separation is the goal.

# ── Leakage warning ─────────────────────────────────────────────────────
# Fit PCA on the TRAINING FOLD only, then transform validation and test.
# Fitting on the whole dataset leaks test-set structure into training - a
# silent, very common cause of scores that do not survive production.
'''),
          example="MNIST digits: 784 pixel features reduce to about 150 components for 95% of the variance, so a kNN classifier gets roughly five times faster with almost no accuracy loss. The reason is that neighbouring pixels are heavily correlated - PCA is exploiting redundancy, not discarding information.",
          pitfalls="Forgetting to centre or standardise; fitting PCA on the full dataset before splitting (leakage); assuming components mean something (PC1 is a weighted blend of all 784 pixels); using PCA when features are already few and interpretable; using t-SNE distances or cluster sizes as if they were real - they are not.",
          followups="'PCA or feature selection?' Selection keeps ORIGINAL features and stays interpretable; PCA builds new combined ones and usually compresses better. 'When does PCA hurt?' When the signal lives in a low-variance direction, or when the model is a tree ensemble - trees are scale-invariant and handle irrelevant features well, so rotating the axes mostly destroys interpretability for no gain."),
    ]

    # ── Neural network fundamentals ───────────────────────────────────────
    entries += [
        Q("ml_concepts", "Neural network basics: from a perceptron to a multi-layer network",
          "INTUITION: a single neuron is logistic regression - multiply each input by a weight, add them up, add a bias, and squash the result. That alone can only draw a straight boundary. Stack neurons into LAYERS and feed one layer's output into the next, with a non-linear squash between them, and the network can bend the boundary into any shape. Early layers learn simple things (edges, in an image), later layers combine them into complex things (a face). PRECISE VERSION: layer l computes a = f(W*x + b), where W is a weight matrix, b a bias vector and f a non-linear activation. The UNIVERSAL APPROXIMATION THEOREM says one hidden layer with enough neurons can approximate any continuous function - but 'enough' can be astronomically many, which is why DEPTH is used instead: each extra layer composes features, so deep networks represent the same functions exponentially more compactly. THE MOST IMPORTANT SENTENCE for an interview: without the non-linear activation, stacking layers is pointless, because a composition of linear maps is just another linear map - a hundred layers would collapse to one. THE MOVING PARTS you should be able to name: forward pass (compute the prediction), loss (measure the error), backward pass (backpropagation - the chain rule assigning blame to every weight), and the optimiser step (gradient descent variants, usually Adam). THE PRACTICAL KNOBS: architecture (depth and width), learning rate (the single most important hyperparameter), batch size, and regularisation - dropout (randomly zero neurons during training so the network cannot over-rely on any one), weight decay, early stopping, and batch/layer normalisation for stable training. WHEN NOT TO USE ONE: small tabular datasets, where gradient-boosted trees usually win outright with a fraction of the effort. Saying that shows judgement rather than enthusiasm.",
          ["ml", "neural-network", "deep-learning", "mlp", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked - the foundation for every deep-learning follow-up.",
          mnemonic="A neuron = weighted sum + bias + squash. Without the SQUASH, stacked layers collapse into one linear layer. Depth composes features. Forward -> loss -> backward -> update. Learning rate is the knob that matters most.",
          code=_c('''
import numpy as np

class MLP:
    """A 2-layer network, trained end to end - the whole idea in 40 lines."""
    def __init__(self, n_in, n_hidden, n_out, seed=0):
        rng = np.random.default_rng(seed)
        # He initialisation: scale by sqrt(2/fan_in) so signals neither explode
        # nor vanish as they pass through layers. Zeros would be fatal - every
        # neuron would compute the same thing and receive the same gradient.
        self.W1 = rng.normal(0, np.sqrt(2 / n_in),     (n_in, n_hidden))
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.normal(0, np.sqrt(2 / n_hidden), (n_hidden, n_out))
        self.b2 = np.zeros(n_out)

    def forward(self, X):
        self.z1 = X @ self.W1 + self.b1
        self.a1 = np.maximum(0, self.z1)               # ReLU - THE non-linearity
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = 1 / (1 + np.exp(-self.z2))           # sigmoid for binary output
        return self.a2

    def backward(self, X, y, lr=0.05):
        m = len(X)
        # Sigmoid + binary cross-entropy: the gradient simplifies to (pred - y).
        dz2 = (self.a2 - y.reshape(-1, 1)) / m
        dW2 = self.a1.T @ dz2
        db2 = dz2.sum(axis=0)
        da1 = dz2 @ self.W2.T
        dz1 = da1 * (self.z1 > 0)                      # ReLU gradient: 1 or 0
        dW1 = X.T @ dz1
        db1 = dz1.sum(axis=0)
        for param, grad in ((self.W1, dW1), (self.b1, db1),
                            (self.W2, dW2), (self.b2, db2)):
            param -= lr * grad                         # gradient descent step

# XOR: the classic problem NO linear model can solve.
X = np.array([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
y = np.array([0., 1., 1., 0.])

net = MLP(2, 8, 1)
for epoch in range(5000):
    net.forward(X)
    net.backward(X, y, lr=0.5)
np.round(net.forward(X).ravel(), 2)      # ~[0.01, 0.99, 0.99, 0.01]

# ── Proof that the activation is what matters ───────────────────────────
# Remove the ReLU (a1 = z1) and the network becomes
#     (X W1 + b1) W2 + b2  =  X (W1 W2) + (b1 W2 + b2)  =  X W' + b'
# i.e. ONE linear layer, which cannot learn XOR no matter how deep it is.
'''),
          example="XOR is the standard demonstration: inputs (0,0) and (1,1) map to 0, while (0,1) and (1,0) map to 1. No straight line separates those four points, so logistic regression is stuck at 75% forever. One hidden layer of two ReLU neurons solves it exactly - which is precisely why the perceptron's inability to do XOR triggered the first AI winter.",
          pitfalls="Initialising all weights to zero (every neuron stays identical); no non-linearity; a learning rate that is too large (loss becomes NaN) or too small (nothing moves); not scaling inputs; reaching for a deep network on 500 rows of tabular data where a gradient-boosted tree is both better and faster.",
          followups="'Why go deep instead of wide?' Depth composes features, so a deep network needs exponentially fewer units for many functions - and it matches the hierarchical structure of images, text and audio. 'What are the vanishing and exploding gradient problems?' Repeated multiplication by small or large derivatives shrinks or blows up the signal reaching early layers; fixed with ReLU, careful initialisation, normalisation layers, residual connections and gradient clipping."),

        Q("ml_concepts", "Backpropagation worked by hand on a tiny network",
          "INTUITION: the network guesses, the guess is wrong by some amount, and the error walks BACKWARD through the layers handing each weight its share of the blame. Backprop is nothing more than the chain rule from calculus applied efficiently: the derivative of the loss with respect to a weight equals how much the loss changes with the output, times how much the output changes with that weight. Doing it backward reuses every intermediate result, which is why it costs about the same as one forward pass instead of one pass per weight. PRECISE VERSION: for each layer, you compute delta - the gradient of the loss with respect to that layer's pre-activation - and then the weight gradient is simply the layer's input times delta. The recursion is delta_l = (W_{l+1}^T delta_{l+1}) * f'(z_l). Two facts that make it click: the FORWARD pass must CACHE its intermediate activations, because the backward pass needs them (that is why training uses far more memory than inference), and the softmax-plus-cross-entropy pair collapses to the beautifully simple gradient (predictions - one_hot_labels), which is why that pair is used everywhere. THE WORKED EXAMPLE BELOW takes a single neuron with two inputs through one complete update with real numbers, which is exactly what an interviewer means by 'walk me through backprop'. The failure modes to name: vanishing gradients (sigmoid's derivative peaks at 0.25, so ten layers multiply to 0.25^10, about one in a million - the early layers stop learning), and exploding gradients (large weights compound the other way, fixed by clipping).",
          ["ml", "backpropagation", "chain-rule", "gradients", "deep-learning", "fundamentals"],
          difficulty="Hard",
          frequency="Very commonly asked in ML/DL interviews - and 'derive it by hand' is a real request.",
          mnemonic="Backprop = the chain rule, computed backward so intermediate results are reused. delta at a layer = (next layer's weights^T @ next delta) * activation'. Weight gradient = input^T @ delta. Cache the forward activations - that is the memory cost of training.",
          code=_c('''
import numpy as np

# ── ONE NEURON, ONE UPDATE, REAL NUMBERS ────────────────────────────────
# Inputs x = [2, 3], weights w = [0.5, -0.5], bias b = 0.1, target y = 1
# Activation: sigmoid.  Loss: binary cross-entropy.

x = np.array([2.0, 3.0]); w = np.array([0.5, -0.5]); b = 0.1; y = 1.0

# FORWARD
z = w @ x + b                      # 0.5*2 + (-0.5)*3 + 0.1 = -0.4
a = 1 / (1 + np.exp(-z))           # sigmoid(-0.4) = 0.4013
loss = -(y * np.log(a) + (1 - y) * np.log(1 - a))     # 0.9130

# BACKWARD - three chain-rule links
dL_da = -(y / a) + (1 - y) / (1 - a)      # dLoss/da   = -2.4917
da_dz = a * (1 - a)                       # dsigmoid   =  0.2403
dL_dz = dL_da * da_dz                     # = a - y    = -0.5987  <- the shortcut
dL_dw = dL_dz * x                         # [-1.1974, -1.7961]
dL_db = dL_dz                             # -0.5987

# UPDATE (learning rate 0.1)
w_new = w - 0.1 * dL_dw                   # [0.6197, -0.3204]
b_new = b - 0.1 * dL_db                   # 0.1599
# Check: the new forward pass gives a = 0.4741 - closer to the target of 1.
# Note dL_dz simplified to (a - y). That cancellation is exactly why sigmoid is
# paired with cross-entropy rather than MSE.


# ── The same idea for a whole layer ─────────────────────────────────────
def backward_layer(dz_next, W_next, z, activation_grad, a_prev):
    """One recursive step of backprop."""
    da   = dz_next @ W_next.T              # blame flows back through the weights
    dz   = da * activation_grad(z)         # through the activation
    dW   = a_prev.T @ dz                   # INPUT to this layer times its delta
    db   = dz.sum(axis=0)
    return dz, dW, db

relu_grad = lambda z: (z > 0).astype(float)

# ── Softmax + cross-entropy: the gradient everyone memorises ────────────
def softmax_ce_grad(logits, y_onehot):
    e = np.exp(logits - logits.max(axis=1, keepdims=True))   # stable softmax
    probs = e / e.sum(axis=1, keepdims=True)
    return (probs - y_onehot) / len(logits)      # that is the WHOLE gradient

# ── Vanishing gradients, in numbers ─────────────────────────────────────
# sigmoid'(z) peaks at 0.25. Through 10 sigmoid layers the gradient reaching
# layer 1 is scaled by at most 0.25^10 = 9.5e-7 - effectively zero, so early
# layers stop learning. ReLU's gradient is exactly 1 for positive inputs, which
# is the single biggest reason deep networks became trainable.
0.25 ** 10
'''),
          example="Gradient checking is the practical skill worth knowing: compare your analytic gradient to (loss(w+eps) - loss(w-eps)) / (2*eps) with eps around 1e-5. If they agree to about six decimal places your derivation is right. Every framework has this built in, and it is how you debug a hand-written layer.",
          examples=[
              "The full single-neuron update, with every number. x = [2,3], w = [0.5,-0.5], b = 0.1, target y = 1, sigmoid activation, binary cross-entropy. FORWARD: z = 0.5*2 + (-0.5)*3 + 0.1 = -0.4; a = sigmoid(-0.4) = 0.4013; loss = -ln(0.4013) = 0.9130. BACKWARD: dL/da = -1/0.4013 = -2.4917; da/dz = a(1-a) = 0.2403; dL/dz = -0.5987, which equals (a - y) exactly. dL/dw = dL/dz * x = [-1.1974, -1.7961]; dL/db = -0.5987. UPDATE with lr = 0.1: w becomes [0.6197, -0.3204], b becomes 0.1599. CHECK: the new z is 0.6197*2 - 0.3204*3 + 0.1 = -0.1218, so a = 0.4696 - closer to 1 than 0.4013. The loss went down; the update was correct.",
              "Why it is computed BACKWARD, which is the efficiency argument. A network with a million weights could be differentiated by perturbing each weight and re-running the forward pass - a million forward passes per training step, which is hopeless. Reverse-mode differentiation computes ALL million gradients in one backward pass costing about the same as one forward pass, because each layer's delta is reused for every weight in that layer. That factor of a million is the entire reason deep learning is feasible, and it is a much better answer to 'what is backprop?' than 'the chain rule'.",
              "The chain rule as blame assignment, in words you can say aloud. 'The loss changed because the output changed. The output changed because the last layer's pre-activation changed. That changed because its weights and its inputs changed. Its inputs were the previous layer's outputs, so the previous layer is partly to blame too.' Each arrow in that sentence is one multiplication in the chain, and delta is literally 'how much of the blame lands on this layer's pre-activation'. Framing it as blame flowing backward is what makes the recursion memorable.",
              "Vanishing gradients, quantified so the fix is obvious. Sigmoid's derivative peaks at 0.25 and is far smaller away from zero. Through 10 sigmoid layers the gradient reaching layer 1 is scaled by AT MOST 0.25^10 = 9.5e-7, and realistically far less - so the early layers receive essentially no learning signal and stay near their random initialisation. ReLU's derivative is exactly 1 for positive inputs, so 1^10 = 1: nothing shrinks. That single number is why networks went from about 5 layers to hundreds, and residual connections (which add an identity path with gradient 1) extend the same idea further.",
              "Gradient checking, which is how you actually debug a hand-written layer. Compare your analytic gradient with the numerical one: (loss(w + eps) - loss(w - eps)) / (2 * eps) with eps around 1e-5. Use the CENTRAL difference, not the one-sided version, because its error is O(eps^2) rather than O(eps). They should agree to about six decimal places; a relative difference above 1e-4 means a real bug. This is slow (one pair of forward passes per weight) so you run it once on a tiny network with a handful of weights, not during training - but it will find a sign error or a transposed matrix in minutes.",
              "Why training needs so much more memory than inference, which follows directly. The backward pass needs each layer's INPUT to compute that layer's weight gradient, so every intermediate activation from the forward pass must be kept alive until the backward pass consumes it. For a large model with a big batch, those activations dominate GPU memory - often more than the weights themselves. The standard mitigation, gradient checkpointing, stores only every k-th activation and RECOMPUTES the others during the backward pass: roughly 30% more compute for a large memory saving. Inference keeps nothing, which is why it fits in a fraction of the memory.",
          ],
          pitfalls="Forgetting to cache forward activations, so the backward pass recomputes everything; applying the activation's derivative to the post-activation value instead of the pre-activation z; averaging over the batch in one place and not another, which silently scales your effective learning rate by the batch size; using MSE with a sigmoid output and then wondering why learning stalls when the model is confidently wrong.",
          followups="'Why does training use so much more memory than inference?' Every intermediate activation is retained for the backward pass; gradient checkpointing trades compute to recompute them instead. 'What is automatic differentiation?' The generalisation frameworks implement - build a graph of primitive operations during the forward pass and apply the chain rule mechanically in reverse, so nobody derives gradients by hand any more."),

        Q("ml_concepts", "Activation functions - which one, and why",
          "WHY THEY EXIST: without a non-linearity between layers, any stack of layers collapses to a single linear map, so the network could never learn a curved boundary. The activation is the bend. THE MENU, and the trade each makes. SIGMOID squashes to (0,1) and is interpretable as a probability, but it SATURATES - for large positive or negative inputs the gradient is nearly zero, so learning stalls - and its output is not zero-centred, which zig-zags the optimisation. Use it only for a binary OUTPUT, never in hidden layers. TANH is the zero-centred version, squashing to (-1,1) with a maximum gradient of 1 rather than 0.25; better than sigmoid for hidden layers, still saturating. RELU, max(0,x), is the default: gradient exactly 1 for positive inputs (so nothing vanishes), trivially cheap, and it produces sparse activations. Its failure is DYING RELU - a neuron pushed permanently negative has zero gradient forever and never recovers, which a too-high learning rate can cause across a whole layer. LEAKY RELU (0.01x for negatives) and its learnable cousin PReLU fix that by keeping a small slope. GELU, which multiplies x by the probability that a standard normal is below it, is a smooth ReLU and is what transformers actually use (as does SiLU/Swish); the smoothness helps optimisation at the top of very deep stacks. SOFTMAX is not a hidden-layer activation at all - it is the multi-class OUTPUT layer, turning logits into probabilities that sum to one. THE DECISION RULE: ReLU for hidden layers by default, GELU or SiLU in transformers, sigmoid for a binary output, softmax for multi-class output, and nothing at all on a regression output.",
          ["ml", "activation", "relu", "gelu", "softmax", "deep-learning", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked in deep-learning interviews - and 'why not sigmoid everywhere?' is the standard follow-up.",
          mnemonic="Hidden layers: ReLU by default, GELU/SiLU in transformers. Output: sigmoid (binary), softmax (multi-class), NOTHING (regression). Sigmoid and tanh SATURATE, so gradients die; ReLU's gradient is 1 - that is why deep nets became trainable.",
          code=_c('''
import numpy as np

def sigmoid(x):    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
def tanh(x):       return np.tanh(x)
def relu(x):       return np.maximum(0, x)
def leaky_relu(x, a=0.01): return np.where(x > 0, x, a * x)
def gelu(x):       # tanh approximation, as used in GPT/BERT
    return 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * x**3)))
def silu(x):       return x * sigmoid(x)          # a.k.a. Swish
def softmax(x):    # OUTPUT layer only; subtract the max for numerical stability
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)

# ── Their gradients, which is where the differences bite ────────────────
def d_sigmoid(x): s = sigmoid(x); return s * (1 - s)      # MAX 0.25
def d_tanh(x):    return 1 - np.tanh(x) ** 2              # max 1.0
def d_relu(x):    return (x > 0).astype(float)            # exactly 1 or 0

x = np.array([-10., -1., 0., 1., 10.])
d_sigmoid(x)   # [4.5e-05, 0.197, 0.25, 0.197, 4.5e-05]  <- saturated at both ends
d_relu(x)      # [0, 0, 0, 1, 1]                          <- no decay for x > 0

# VANISHING GRADIENT, quantified: through 10 sigmoid layers the best possible
# gradient scaling is 0.25**10 = 9.5e-07. Through 10 ReLU layers it is 1.0.
0.25 ** 10, 1.0 ** 10

# ── Dying ReLU, and the fix ─────────────────────────────────────────────
# One large update pushes a neuron's pre-activation permanently negative:
#   relu(-3) = 0  and  d_relu(-3) = 0  -> zero gradient forever, neuron dead.
leaky_relu(np.array([-3.0]))            # -0.03: small, but NOT zero, so the
                                        # gradient (0.01) can still revive it

# ── Choosing the OUTPUT activation ──────────────────────────────────────
#   regression        -> none (a raw linear output; clamping caps predictions)
#   binary            -> sigmoid + binary cross-entropy
#   multi-class       -> softmax + categorical cross-entropy
#   MULTI-LABEL       -> per-label SIGMOID, not softmax: softmax forces the
#                        probabilities to sum to 1, which is wrong when an image
#                        can be both "beach" and "sunset"
'''),
          example="The multi-label trap is worth remembering: tagging a photo with 'beach' AND 'sunset' needs an independent sigmoid per tag. Using softmax forces the tags to compete for a fixed budget of probability, so the more tags an image genuinely has, the lower each one scores - a subtle bug that shows up as 'my model is under-confident on rich images'.",
          pitfalls="Sigmoid in hidden layers of a deep net; softmax for multi-label; forgetting to subtract the max in softmax (exp overflows to inf); an activation on a regression output, which silently caps the range; a learning rate so high it kills a whole ReLU layer, which shows up as a loss that plateaus at a bad value and never moves.",
          followups="'Why do transformers use GELU rather than ReLU?' It is smooth, so the gradient is non-zero near the origin, which empirically trains large models a little better; the gain is small but consistent at scale. 'What if my ReLU network is not learning at all?' Check for dying ReLUs (count zero activations per layer), lower the learning rate, and switch to Leaky ReLU as a diagnostic."),

        Q("ml_concepts", "Loss functions - which to use when, and why the pairing matters",
          "The loss is the ONLY thing training optimises, so choosing it is choosing what your model cares about. REGRESSION. MSE (squared error) punishes big errors quadratically, so it chases outliers and its optimum is the MEAN; it is smooth and easy to optimise. MAE (absolute error) treats every euro of error equally, so its optimum is the MEDIAN and it is robust to outliers, at the cost of a non-smooth gradient at zero. HUBER is quadratic near zero and linear far out - the practical compromise, with delta as the crossover. Also worth naming: for skewed targets like price or traffic, predict log(y) and you effectively optimise relative rather than absolute error. CLASSIFICATION. Binary cross-entropy for two classes, categorical cross-entropy for many; both punish confident wrong answers severely, which is the behaviour you want, and both give a clean gradient when paired with sigmoid/softmax. FOCAL LOSS down-weights easy examples and is the standard answer for extreme class imbalance in detection. HINGE LOSS is the SVM's, caring only that the correct class wins by a margin. THE PAIRING FACT that interviewers dig for: MSE with a sigmoid output is non-convex and its gradient vanishes exactly when the model is confidently wrong, which is why sigmoid pairs with cross-entropy - and the resulting gradient is simply (prediction - target). RANKING AND EMBEDDINGS: triplet or contrastive loss, which optimise relative distances rather than absolute labels, and that is what powers face recognition and the embeddings behind semantic search. THE HABIT WORTH FORMING: your loss should reflect the BUSINESS cost. If a false negative costs ten times a false positive, either weight the classes in the loss or tune the threshold afterwards - do not report accuracy and hope.",
          ["ml", "loss-function", "mse", "cross-entropy", "focal-loss", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked - 'which loss would you use and why?' is a standard probe.",
          mnemonic="Regression: MSE chases the MEAN (outlier-sensitive), MAE the MEDIAN (robust), Huber between. Classification: cross-entropy, always. The pairing rule - sigmoid/softmax WITH cross-entropy gives the clean gradient (pred - target); MSE with a sigmoid stalls.",
          code=_c('''
import numpy as np

# ── Regression losses, and what they optimise toward ────────────────────
def mse(y, p):   return np.mean((y - p) ** 2)
def mae(y, p):   return np.mean(np.abs(y - p))
def huber(y, p, delta=1.0):
    e = np.abs(y - p)
    return np.mean(np.where(e <= delta, 0.5 * e**2, delta * (e - 0.5*delta)))

y = np.array([10., 12., 11., 13., 200.])          # one outlier
# The constant prediction each loss prefers:
np.mean(y), np.median(y)                          # 49.2  vs  12.0
# MSE would have you predict ~49 (wrong for 4 of the 5 points) because the
# single outlier contributes (200-49)^2. MAE predicts 12 and ignores it.

# ── Classification ──────────────────────────────────────────────────────
def binary_cross_entropy(y, p, eps=1e-15):
    p = np.clip(p, eps, 1 - eps)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

binary_cross_entropy(np.array([1.]), np.array([0.99]))   # 0.01  - confident, right
binary_cross_entropy(np.array([1.]), np.array([0.50]))   # 0.69  - unsure
binary_cross_entropy(np.array([1.]), np.array([0.01]))   # 4.61  - confident, WRONG
# Note the asymmetry: being confidently wrong costs ~460x being confidently right.

def focal_loss(y, p, gamma=2.0, alpha=0.25, eps=1e-15):
    """For extreme imbalance: (1-p)^gamma shrinks the loss on EASY examples,
    so the 99.9% easy negatives stop drowning out the rare positives."""
    p = np.clip(p, eps, 1 - eps)
    pt = np.where(y == 1, p, 1 - p)
    w  = np.where(y == 1, alpha, 1 - alpha)
    return -np.mean(w * (1 - pt) ** gamma * np.log(pt))

# An easy negative predicted at 0.01 contributes (1-0.99)^2 = 0.0001 of its
# usual weight - a 10,000x reduction. That is how one-stage detectors train.

# ── Class weighting: encode the BUSINESS cost in the loss ───────────────
def weighted_bce(y, p, w_pos=10.0, eps=1e-15):
    p = np.clip(p, eps, 1 - eps)
    return -np.mean(w_pos * y * np.log(p) + (1 - y) * np.log(1 - p))
# w_pos = 10 says "missing a fraud costs ten times a false alarm" - and the
# model optimises for that, instead of you patching it at the threshold later.

# ── The pairing rule, made explicit ─────────────────────────────────────
# sigmoid + BCE      -> dLoss/dz = (p - y)          clean, never vanishes
# sigmoid + MSE      -> dLoss/dz = (p - y) * p(1-p) vanishes when p is near 0/1,
#                                                   i.e. exactly when wrong
'''),
          example="Predicting delivery time with MSE, where 1% of deliveries are stuck for days. The squared term makes those outliers dominate, so the model shifts every ordinary prediction upward to hedge against them and the typical delivery estimate becomes useless. Switch to MAE or Huber and the typical case gets accurate again - the loss, not the model, was the problem.",
          pitfalls="MSE on data with heavy-tailed outliers; cross-entropy without clipping (log(0) is -inf); optimising accuracy-shaped losses on imbalanced data; using a loss that ignores the asymmetric cost of the two error types and then being surprised the model 'does not care about fraud'; forgetting that a loss you cannot differentiate (accuracy, F1) cannot be optimised directly - you optimise a surrogate and threshold afterwards.",
          followups="'Why can you not train directly on F1 or accuracy?' They are step functions of the predictions with zero gradient almost everywhere; you optimise cross-entropy and then tune the threshold to maximise F1 on validation. 'How do you handle a regression target spanning many orders of magnitude?' Train on log(y) - it converts absolute error into relative error, which is usually what the business means."),
    ]

    # ── Applied / evaluation ──────────────────────────────────────────────
    entries += [
        Q("ml_concepts", "Data leakage - the bug that makes a terrible model look excellent",
          "THE DEFINITION: leakage is when information that will not be available at prediction time sneaks into training. The symptom is unmistakable and seductive - suspiciously high validation scores that collapse in production. THE SIX WAYS IT HAPPENS, and you should be able to name them. (1) TARGET LEAKAGE - a feature that is a consequence of the label. Predicting hospital readmission with a 'discharge medication changed' flag recorded after readmission; predicting churn with 'account_closed_date'. The tell is a single feature with implausible importance. (2) TRAIN-TEST CONTAMINATION - fitting a scaler, imputer, encoder or PCA on the FULL dataset before splitting, so test statistics leak into the transform. The fix is a Pipeline, so every transform is fitted inside each fold. (3) TEMPORAL LEAKAGE - random splitting time-series data, so you train on the future to predict the past. Always split by TIME. (4) DUPLICATE OR NEAR-DUPLICATE ROWS spanning the split (the same customer twice, augmented copies of the same image), which is really testing on the training set. Group-aware splitting fixes it. (5) GROUP LEAKAGE - the same patient, user or device in both sets, so the model memorises the entity rather than the pattern. (6) LEAKAGE THROUGH FEATURE SELECTION or hyperparameter tuning on the test set, which is a slower version of the same disease. THE DISCIPLINE THAT PREVENTS ALL SIX: split first, then do everything else inside the split; for every feature, ask 'would I know this value at the moment I need the prediction?'; and hold out a final test set you touch exactly once. Say that last rule out loud - interviewers weight it heavily.",
          ["ml", "data-leakage", "validation", "pitfalls", "production", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked at Amazon and Google - a favourite because it separates people who have shipped models from people who have only trained them.",
          mnemonic="Leakage = information at training time you will not have at prediction time. Split FIRST, transform INSIDE the split (use a Pipeline), split time-series BY TIME, group by entity, and for every feature ask 'would I know this at prediction time?'. 99% accuracy is a bug report.",
          code=_c('''
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (cross_val_score, train_test_split,
                                     TimeSeriesSplit, GroupKFold)

X = np.random.rand(1000, 10); y = np.random.randint(0, 2, 1000)

# ── WRONG: the scaler sees the test set's mean and variance ─────────────
X_scaled = StandardScaler().fit_transform(X)          # fitted on EVERYTHING
X_tr, X_te, y_tr, y_te = train_test_split(X_scaled, y)
# Optimistic score. In production the scaler has never seen the new data.

# ── RIGHT: a pipeline, so every step is fitted per fold ─────────────────
pipe = Pipeline([
    ("impute", SimpleImputer(strategy="median")),     # median from the FOLD
    ("scale",  StandardScaler()),                     # mean/sd from the FOLD
    ("model",  LogisticRegression()),
])
cross_val_score(pipe, X, y, cv=5)     # each fold fits its own transforms

# ── TEMPORAL data: never split at random ────────────────────────────────
# WRONG: train_test_split(X, y, shuffle=True) on daily sales - you train on
#        December to predict November.
for train_idx, test_idx in TimeSeriesSplit(n_splits=5).split(X):
    assert train_idx.max() < test_idx.min()          # train is always EARLIER

# ── GROUP leakage: the same entity in both sets ─────────────────────────
patient_ids = np.random.randint(0, 200, 1000)        # 5 rows per patient
cross_val_score(pipe, X, y, cv=GroupKFold(5), groups=patient_ids)
# Without groups, the model memorises patients rather than learning medicine.

# ── TARGET leakage: the detector ────────────────────────────────────────
def leakage_smell_test(model, feature_names, X, y):
    """One feature carrying nearly all the signal is a red flag, not a win."""
    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier(n_estimators=100).fit(X, y)
    ranked = sorted(zip(feature_names, rf.feature_importances_),
                    key=lambda t: -t[1])
    top_name, top_importance = ranked[0]
    if top_importance > 0.5:
        print(f"SUSPECT: '{top_name}' carries {top_importance:.0%} of the signal."
              f" Ask: is it recorded BEFORE or AFTER the label?")
    return ranked

# The one question that catches most leakage, per feature:
#   "At the moment I must make this prediction in production, do I have
#    this value yet?"  If not, it cannot be a feature.
'''),
          example="A famous class of case: a model predicting cancer from scans reached near-perfect accuracy because the scanner used for confirmed patients stamped a slightly different image border. The model learned the hospital's workflow, not the disease. That is target leakage through a feature nobody listed as a feature - and it is why an implausibly good score should trigger investigation rather than celebration.",
          pitfalls="Fitting any transform before splitting; random splits on time series; oversampling (SMOTE) before the split, so synthetic copies of test rows appear in training; tuning hyperparameters against the test set repeatedly until it is effectively a training set; deduplicating after splitting rather than before.",
          followups="'Your model scores 0.99 AUC - what do you do?' Assume leakage until proven otherwise: inspect top feature importances, check the timeline of each feature, verify the split strategy, and try training without the suspicious feature. 'How do you catch it before production?' A strict backtest on a period the model has never seen, plus comparing the offline score to the first week of online performance - a large gap is the leakage alarm."),

        Q("ml_concepts", "Evaluation metrics: the complete map, and how to choose",
          "The rule underneath everything: pick the metric that matches the DECISION and the COST of each error, then justify it. CLASSIFICATION. Accuracy is only meaningful on balanced data - 99% accuracy is trivial when 99% of transactions are legitimate. PRECISION (of those we flagged, how many were real) is what you optimise when a false positive is expensive - blocking a genuine customer's card. RECALL (of the real cases, how many did we catch) is what you optimise when a false negative is expensive - missing a tumour. F1 is their harmonic mean, which stays low if either is bad; F-beta lets you weight one over the other. ROC-AUC is threshold-independent and answers 'how well does the model RANK positives above negatives?', but it is optimistic under heavy imbalance because the false-positive rate has a huge denominator - so use PR-AUC when positives are rare. LOG LOSS measures the quality of the PROBABILITIES, which matters when you use them for expected-value decisions rather than just a class. REGRESSION. RMSE (same units as the target, outlier-sensitive), MAE (robust, and 'the typical error is X' is the sentence a stakeholder understands), MAPE (relative error, but it explodes when the true value is near zero), R-squared (share of variance explained, and it never decreases when you add features). RANKING AND RECOMMENDATION: Precision@k and Recall@k, MAP, NDCG (which rewards putting the best item highest, with a logarithmic position discount), MRR. CLUSTERING: silhouette, Davies-Bouldin, and adjusted Rand index if you happen to have ground truth. THE HABIT: quote a metric with the BASELINE beside it. 'AUC 0.82' means nothing on its own; 'AUC 0.82 versus 0.71 for the current rules engine, on last month's held-out data' is a result.",
          ["ml", "metrics", "evaluation", "precision", "recall", "auc", "fundamentals"],
          difficulty="Medium",
          frequency="Very commonly asked - metrics questions appear in essentially every ML interview.",
          mnemonic="False positive expensive -> PRECISION. False negative expensive -> RECALL. Rare positives -> PR-AUC, not ROC-AUC. Probabilities used for decisions -> log loss. Regression: RMSE punishes outliers, MAE is the typical error. Always quote a BASELINE.",
          code=_c('''
import numpy as np

def confusion(y, pred):
    tp = int(((pred == 1) & (y == 1)).sum());  fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum());  tn = int(((pred == 0) & (y == 0)).sum())
    return tp, fp, fn, tn

def report(y, pred):
    tp, fp, fn, tn = confusion(y, pred)
    precision = tp / (tp + fp) if tp + fp else 0.0     # of flagged, how many real
    recall    = tp / (tp + fn) if tp + fn else 0.0     # of real, how many caught
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": (tp + tn) / len(y), "precision": precision,
            "recall": recall, "f1": f1,
            "specificity": tn / (tn + fp) if tn + fp else 0.0}

# ── The 99%-accuracy trap, in numbers ───────────────────────────────────
y = np.array([0] * 990 + [1] * 10)          # 1% fraud
always_zero = np.zeros(1000)
report(y, always_zero)
# accuracy 0.99, recall 0.0 - a model that catches NO fraud looks excellent on
# accuracy. This is why accuracy is banned from imbalanced problems.

# ── ROC-AUC vs PR-AUC under imbalance ───────────────────────────────────
# 10 positives, 990 negatives. A model flags 10 true positives and 90 false ones.
#   FPR = 90/990  = 0.09  -> ROC looks great (small denominator effect)
#   Precision = 10/100 = 0.10 -> PR-AUC tells the truth: 9 of 10 alerts are junk
# Rule: when the positive class is rare and you care about the ALERTS you
# generate, report PR-AUC.

# ── Choosing a threshold from COST, not from 0.5 ────────────────────────
def best_threshold(y, probs, cost_fp=1.0, cost_fn=10.0):
    """Missing a fraud costs 10x a false alarm -> the optimal threshold is
    far below 0.5, and you can compute exactly where."""
    best, best_cost = 0.5, float("inf")
    for t in np.linspace(0.01, 0.99, 99):
        tp, fp, fn, tn = confusion(y, (probs >= t).astype(int))
        cost = fp * cost_fp + fn * cost_fn
        if cost < best_cost:
            best, best_cost = t, cost
    return best, best_cost

# ── Regression ──────────────────────────────────────────────────────────
def rmse(y, p): return float(np.sqrt(np.mean((y - p) ** 2)))
def mae(y, p):  return float(np.mean(np.abs(y - p)))
def mape(y, p): return float(np.mean(np.abs((y - p) / np.clip(np.abs(y), 1e-9, None))) * 100)
def r2(y, p):   return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())

# ── Ranking: NDCG, because position matters ─────────────────────────────
def dcg(relevances):
    return sum(r / np.log2(i + 2) for i, r in enumerate(relevances))

def ndcg(relevances, k=10):
    ideal = sorted(relevances, reverse=True)[:k]
    return dcg(relevances[:k]) / (dcg(ideal) or 1.0)

ndcg([3, 2, 3, 0, 1, 2])     # rewards putting the most relevant items FIRST
'''),
          example="Cancer screening versus spam. Screening: a missed tumour is catastrophic and a false alarm costs one follow-up test, so optimise RECALL and accept low precision. Spam: a lost real email is worse than a seen spam, so optimise PRECISION. Same maths, opposite thresholds - and the choice is a business decision, not a modelling one. Saying that sentence is the whole point of the question.",
          examples=[
              "The 99%-accuracy trap, with the arithmetic. 1,000 transactions, 10 of them fraud. A model that predicts 'not fraud' for everything scores 990/1000 = 99% accuracy, and catches zero fraud: precision undefined, recall 0.0, F1 0.0. Any candidate reporting accuracy here has told the interviewer they do not understand the problem. The moment the positive class is under about 10% of the data, quote precision, recall and PR-AUC instead, and say why.",
              "Precision and recall computed from one confusion matrix. Out of 1,000 transactions with 10 frauds, the model flags 100 and 8 of them are genuinely fraud. TP = 8, FP = 92, FN = 2, TN = 898. Precision = 8/100 = 0.08 (92% of the alerts are wasted analyst time), recall = 8/10 = 0.80 (we caught 8 of 10 frauds), F1 = 2*0.08*0.80/0.88 = 0.145. Whether this model is good depends entirely on what an analyst hour costs versus what a missed fraud costs - and computing that expected cost is the answer, not the F1.",
              "Why ROC-AUC flatters an imbalanced model, in the same numbers. With 990 negatives, those 92 false positives give a false-positive rate of 92/990 = 0.093 - which looks excellent on an ROC curve because the denominator is huge. PRECISION uses the alerts as the denominator (92/100) and reports the truth: nine of ten alerts are junk. So ROC-AUC can sit at 0.95 while the model is operationally useless. Rule of thumb: when the positive class is rare AND you care about the alerts you generate, PR-AUC is the honest curve.",
              "Choosing a threshold from cost, worked. A fraud model with probabilities. At threshold 0.5: 8 caught, 2 missed, 92 false alarms. At 0.3: 9 caught, 1 missed, 210 false alarms. At 0.7: 6 caught, 4 missed, 30 false alarms. With a missed fraud at 500 euro and a review at 5 euro: 0.5 costs 2*500 + 92*5 = 1,460; 0.3 costs 1*500 + 210*5 = 1,550; 0.7 costs 4*500 + 30*5 = 2,150. Threshold 0.5 wins here, but only because of those specific costs - change the review cost to 2 euro and 0.3 becomes best. The point is that the threshold is computed, not assumed.",
              "Regression metrics, and which sentence each one gives a stakeholder. Predicting delivery time in minutes, errors [2, 3, 1, 4, 60]. MAE = 14 minutes ('the typical error is 14 minutes' - though the median error is 3, so quote that too). RMSE = sqrt((4+9+1+16+3600)/5) = 26.8 minutes, dominated entirely by the one 60-minute miss. If those big misses are the thing customers complain about, RMSE is the right metric because it punishes them; if they are data errors, MAE is. MAPE would be a bad choice if any true value is near zero, since dividing by it explodes.",
              "NDCG, and why ranking needs its own metric. Search returns 5 results with relevance [3, 2, 3, 0, 1]. DCG = 3/log2(2) + 2/log2(3) + 3/log2(4) + 0/log2(5) + 1/log2(6) = 3 + 1.26 + 1.5 + 0 + 0.39 = 6.15. The ideal ordering [3,3,2,1,0] gives an ideal DCG of 3 + 1.89 + 1 + 0.43 + 0 = 6.32, so NDCG = 0.97. The logarithmic discount is the point: moving a relevant result from position 5 to position 1 improves the score far more than moving it from position 50 to position 46, which matches how users actually behave.",
          ],
          pitfalls="Reporting accuracy on imbalanced data; ROC-AUC when positives are under about 5% of the data; a fixed 0.5 threshold with no cost analysis; comparing metrics computed on different splits; reporting a metric with no baseline; optimising a metric the business never asked for.",
          followups="'Your model has 0.95 precision and 0.3 recall - is that good?' It depends entirely on the cost ratio; ask what happens on a miss versus a false alarm, then compute the expected cost at several thresholds. 'How do you evaluate a model with no labels?' Proxy signals and human evaluation, plus monitoring input drift and downstream business metrics."),

        Q("ml_concepts", "Diagnosing a model with learning curves (is it bias or variance?)",
          "THE PROBLEM: your model scores badly and you have a dozen possible fixes - more data, more features, fewer features, a bigger model, more regularisation. Guessing wastes weeks. LEARNING CURVES tell you which family of fix to reach for, by plotting training and validation error against the amount of TRAINING DATA used. READ THEM LIKE THIS. HIGH BIAS (underfitting): training error is high AND validation error is high, and the two curves have converged close together at a bad level. More data will NOT help - the flat line is the model's ceiling. Fix by increasing capacity: a more complex model, more or better features, interaction terms, less regularisation, longer training. HIGH VARIANCE (overfitting): training error is low, validation error is much higher, and there is a big persistent gap that narrows slowly as data grows. More data WILL help, and so will regularisation, dropout, early stopping, simpler models, or feature reduction. THE THIRD CURVE worth plotting is validation error against training EPOCHS: if it falls and then rises while training error keeps falling, that is the classic overfitting turn and the minimum is where early stopping should fire. THE PRACTICAL ORDER for a diagnosis, which is a great thing to narrate in an interview: (1) establish a baseline and the human/irreducible error level, (2) check training error - if it is far from that level you have bias, so fix capacity first, (3) only then check the train-validation gap for variance, (4) if both are fine offline but production is bad, you have distribution shift or leakage, not a bias/variance problem at all. That last branch is what distinguishes someone who has deployed a model.",
          ["ml", "learning-curves", "bias-variance", "debugging", "diagnostics", "fundamentals"],
          difficulty="Medium",
          frequency="Commonly asked as 'your model is not working, what do you do?' - a favourite Amazon and Google diagnostic question.",
          mnemonic="Both errors high and together = BIAS (underfit) -> more capacity, and more data will NOT help. Train low, validation high with a gap = VARIANCE (overfit) -> more data or more regularisation. Validation curve turning back up over epochs = stop there.",
          code=_c('''
import numpy as np
from sklearn.model_selection import learning_curve, validation_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import Ridge

def diagnose(model, X, y, cv=5):
    sizes, train_scores, val_scores = learning_curve(
        model, X, y, cv=cv, train_sizes=np.linspace(0.1, 1.0, 8),
        scoring="neg_mean_squared_error")
    train_err = -train_scores.mean(axis=1)
    val_err   = -val_scores.mean(axis=1)

    final_train, final_val = train_err[-1], val_err[-1]
    gap = final_val - final_train
    still_improving = (val_err[-2] - val_err[-1]) > 0.01 * val_err[-1]

    if final_train > acceptable_error():                 # cannot even fit train
        return ("HIGH BIAS: more data will not help. Add capacity - a richer "
                "model, better features, interaction terms, less regularisation.")
    if gap > 0.2 * final_train:
        return ("HIGH VARIANCE: " +
                ("more data is still helping, so collect more. " if still_improving
                 else "more data has stopped helping, so regularise, simplify, "
                      "or reduce features."))
    return "Bias and variance both acceptable - look at data quality or shift."

def acceptable_error():
    """Anchor on the irreducible/human error level, not on zero."""
    return 0.05

# ── Validation curve: sweep ONE hyperparameter to see the U ─────────────
X = np.random.rand(400, 5); y = X[:, 0] * 3 + np.random.normal(0, .1, 400)
alphas = np.logspace(-4, 3, 8)
train_s, val_s = validation_curve(
    make_pipeline(StandardScaler(), PolynomialFeatures(3), Ridge()),
    X, y, param_name="ridge__alpha", param_range=alphas, cv=5)
# Small alpha  -> train error tiny, validation error large   (overfit)
# Large alpha  -> both errors large                          (underfit)
# The validation minimum in between is your alpha. This U-shape IS the
# bias-variance trade-off, drawn.

# ── Early stopping: the same idea over EPOCHS ───────────────────────────
def train_with_early_stopping(model, X_tr, y_tr, X_val, y_val, patience=5):
    best, best_epoch, wait, best_weights = float("inf"), 0, 0, None
    for epoch in range(1000):
        model.partial_fit(X_tr, y_tr)
        val_loss = model.loss(X_val, y_val)
        if val_loss < best - 1e-4:
            best, best_epoch, wait = val_loss, epoch, 0
            best_weights = model.get_weights()          # keep the BEST, not the last
        else:
            wait += 1
            if wait >= patience:
                model.set_weights(best_weights)         # roll back
                break
    return model, best_epoch
'''),
          example="A concrete read: training RMSE 12.0 and validation RMSE 12.4 when human experts achieve about 3.0. The gap is tiny, so variance is not the problem - the model simply cannot fit, and collecting another million rows would change nothing. The fix is capacity or features. Candidates who jump to 'get more data' by reflex fail exactly this question.",
          pitfalls="Comparing training error to zero instead of to the irreducible/human error; plotting only the final scores rather than curves, which hides the trend; using accuracy on imbalanced data as the curve's metric; changing two things at once so you cannot tell which helped; forgetting that a bad validation score with a good training score can also be leakage or a broken split rather than variance.",
          followups="'Both errors are low but production is bad - now what?' Distribution shift or leakage; compare the training feature distributions to live traffic and check every feature's availability at prediction time. 'How much data do you need?' Extrapolate the validation curve - if it has flattened, more data is not the constraint, and that is a defensible answer to give a manager."),

        Q("ml_concepts", "Hyperparameter tuning: grid, random, Bayesian - and doing it honestly",
          "THE DISTINCTION FIRST: parameters are LEARNED from data (weights, coefficients, split points); hyperparameters are SET BY YOU before training (learning rate, tree depth, k, regularisation strength, number of layers). GRID SEARCH tries every combination on a predefined grid - exhaustive, reproducible, and exponential: five hyperparameters with five values each is 3,125 fits, and with 5-fold cross-validation that is 15,625 trainings. RANDOM SEARCH samples combinations at random and, counter-intuitively, usually beats grid search for the same budget. The reason is worth being able to explain: most hyperparameters do not matter much, and a grid wastes its budget re-testing the same value of the important one; random search tries a different value of every parameter on every trial, so it explores the important dimension far more finely. BAYESIAN OPTIMISATION (Optuna, Hyperopt, scikit-optimize) builds a probabilistic model of how the score depends on the hyperparameters and picks the next trial where improvement is most likely - clearly better when each training run is expensive, which is exactly the deep-learning case. SUCCESSIVE HALVING / HYPERBAND is the other trick: start many configurations cheaply (few epochs, a data subset), kill the worst half, and give the survivors more budget. THE HONESTY RULES, which is what interviewers actually check. Tune on a VALIDATION set (or cross-validation), never on the test set, and touch the test set once at the very end - every time you tune against it, it becomes training data and your reported score becomes optimistic. Use NESTED cross-validation when you need an unbiased estimate of a tuned model. And always sample the learning rate and regularisation strength on a LOG scale, since what matters is the order of magnitude.",
          ["ml", "hyperparameters", "tuning", "cross-validation", "optuna", "fundamentals"],
          difficulty="Medium",
          frequency="Commonly asked in ML engineering interviews; the 'why does random search beat grid search?' question is a favourite.",
          mnemonic="Parameters are LEARNED, hyperparameters are CHOSEN. Random beats grid for the same budget because only a few hyperparameters matter. Bayesian when each run is expensive. Sample learning rate on a LOG scale. Tune on validation; touch the test set ONCE.",
          code=_c('''
import numpy as np
from scipy.stats import loguniform, randint
from sklearn.model_selection import (GridSearchCV, RandomizedSearchCV,
                                     cross_val_score, KFold)
from sklearn.ensemble import GradientBoostingClassifier

X = np.random.rand(800, 12); y = np.random.randint(0, 2, 800)

# ── Grid: exhaustive and exponential ────────────────────────────────────
grid = GridSearchCV(
    GradientBoostingClassifier(),
    {"n_estimators": [100, 300], "max_depth": [2, 3, 5],
     "learning_rate": [0.01, 0.1]},          # 2*3*2 = 12 combos x 5 folds = 60 fits
    cv=5, scoring="roc_auc", n_jobs=-1).fit(X, y)

# ── Random: same budget, better coverage of what matters ────────────────
rand = RandomizedSearchCV(
    GradientBoostingClassifier(),
    {"n_estimators":  randint(50, 500),
     "max_depth":     randint(2, 8),
     "learning_rate": loguniform(1e-3, 3e-1),   # LOG scale - orders of magnitude
     "subsample":     [0.6, 0.8, 1.0]},
    n_iter=30, cv=5, scoring="roc_auc", n_jobs=-1, random_state=0).fit(X, y)

# WHY random wins: with 2 hyperparameters where only ONE matters, a 5x5 grid
# tries just 5 DISTINCT values of the important one (25 fits). 25 random trials
# try 25 distinct values of it. Same cost, five times the resolution.

# ── NESTED CV: the honest way to report a tuned model's score ───────────
def nested_cv_score(X, y):
    outer = KFold(5, shuffle=True, random_state=0)
    scores = []
    for train_idx, test_idx in outer.split(X):
        search = RandomizedSearchCV(GradientBoostingClassifier(),
                                    {"max_depth": randint(2, 8),
                                     "learning_rate": loguniform(1e-3, 3e-1)},
                                    n_iter=10, cv=3, n_jobs=-1)
        search.fit(X[train_idx], y[train_idx])          # tuning INSIDE the fold
        scores.append(search.score(X[test_idx], y[test_idx]))
    return float(np.mean(scores)), float(np.std(scores))
# The inner loop tunes; the outer loop measures. Without nesting, the reported
# score is optimistic because the tuning already saw that data.

# ── Bayesian, when each run costs minutes or hours ──────────────────────
# import optuna
# def objective(trial):
#     params = {
#         "max_depth":     trial.suggest_int("max_depth", 2, 12),
#         "learning_rate": trial.suggest_float("lr", 1e-4, 0.3, log=True),
#         "subsample":     trial.suggest_float("subsample", 0.5, 1.0),
#     }
#     return cross_val_score(GradientBoostingClassifier(**params), X, y, cv=3).mean()
# study = optuna.create_study(direction="maximize")
# study.optimize(objective, n_trials=50)     # each trial LEARNS from the last

# ── Order of attack, for a fixed budget ─────────────────────────────────
# 1. learning rate (dominates everything else)
# 2. model capacity (depth / number of estimators / hidden size)
# 3. regularisation (alpha, dropout, subsample)
# 4. everything else - usually worth very little
'''),
          example="Random-versus-grid in one calculation: 25 trials on two hyperparameters where only the learning rate matters. A 5x5 grid tests five distinct learning rates. Random search tests 25 distinct ones. Identical compute, five times the resolution on the dimension that decides your result - that is the whole argument, and it generalises: the more irrelevant hyperparameters you have, the worse grid search gets.",
          pitfalls="Tuning against the test set (the most common integrity failure in student projects); a linear range for the learning rate; huge grids over parameters that do not matter; forgetting that cross-validation multiplies your fit count by k; not fixing the random seed, so an apparent improvement is noise; reporting the best cross-validation score as the expected production score - it is biased upward by the selection itself.",
          followups="'How do you tune when one training run takes eight hours?' Successive halving/Hyperband on a data subset and few epochs, then Bayesian optimisation on the survivors. 'Is the difference between your best two configurations real?' Compare the fold-level scores with their standard deviation - differences smaller than the fold noise are not results."),

        Q("ml_concepts", "The applied ML question: taking a model from notebook to production",
          "Amazon and Google both ask a version of 'you have a model that works in a notebook - now what?', and the answer is a lifecycle, not an algorithm. (1) PROBLEM FRAMING - what decision does this change, what is the business metric, and what is the current baseline (often a rules engine or a human). If you cannot state how the decision changes, do not build the model. (2) DATA - where does it come from, how fresh is it, who owns it, what does the label actually mean and when is it available; the label definition is where most projects go wrong ('churn' means what, exactly, and measured how many days out?). (3) FEATURES - and here is the production-specific trap, TRAINING-SERVING SKEW: features computed in a batch job with pandas and recomputed at request time in a different service will drift apart, so you either share the transformation code or use a feature store. Any feature that requires data unavailable at request time is disqualified regardless of how predictive it looks. (4) TRAINING - reproducibility (seeds, pinned data snapshots, versioned code and artefacts) so the model you deploy is one you can rebuild. (5) EVALUATION - offline metrics on a time-based holdout, then a shadow deployment (score live traffic without acting on it) and finally an A/B test on the BUSINESS metric, which is the only one that counts. (6) SERVING - batch (precompute nightly, serve from a table: cheap and simple) versus real time (a service behind an API with a latency budget); most teams should start with batch. (7) MONITORING, which is what junior answers omit entirely: prediction distribution, input drift, feature availability and freshness, latency, and delayed ground truth for actual accuracy. (8) RETRAINING - on a schedule or triggered by drift, with the ability to roll back to the previous model in one step.",
          ["ml", "mlops", "production", "deployment", "monitoring", "system-design"],
          difficulty="Hard",
          frequency="Very commonly asked at Amazon and Google for any applied-ML or ML-engineering role.",
          mnemonic="Frame -> Data -> Features -> Train -> Evaluate offline -> Shadow -> A/B -> Serve -> Monitor -> Retrain. The two production-only ideas juniors miss: TRAINING-SERVING SKEW and MONITORING FOR DRIFT. Start with batch scoring unless latency truly demands otherwise.",
          code=_c('''
# ── 3. TRAINING-SERVING SKEW: the fix is SHARED code, not discipline ────
# One transformation module used by BOTH the training job and the API.
def build_features(raw: dict) -> dict:
    """The single source of truth. Import this in training AND in serving."""
    return {
        "amount_log":   __import__("math").log1p(raw["amount"]),
        "hour_of_day":  raw["ts"].hour,
        "is_weekend":   int(raw["ts"].weekday() >= 5),
        "days_since_signup": (raw["ts"] - raw["signup_ts"]).days,
    }
# If training uses pandas and the API re-implements this in Java, the two WILL
# diverge - a different rounding rule or timezone is enough - and the model
# silently degrades with no error anywhere.

# ── 5/8. MONITORING: drift, before accuracy is even available ───────────
import numpy as np

def psi(expected, actual, bins=10):
    """Population Stability Index: how far has this feature's distribution
    moved since training? <0.1 stable, 0.1-0.25 investigate, >0.25 act."""
    cuts = np.quantile(expected, np.linspace(0, 1, bins + 1))
    cuts[0], cuts[-1] = -np.inf, np.inf
    e = np.histogram(expected, cuts)[0] / len(expected) + 1e-6
    a = np.histogram(actual,   cuts)[0] / len(actual)   + 1e-6
    return float(((a - e) * np.log(a / e)).sum())

class ModelMonitor:
    """Ground truth arrives late (a chargeback takes 30 days), so watch what
    you CAN see immediately: inputs, outputs and health."""
    def __init__(self, train_features, train_scores):
        self.train_features, self.train_scores = train_features, train_scores

    def check(self, live_features, live_scores):
        alerts = []
        for name, ref in self.train_features.items():
            score = psi(ref, live_features[name])
            if score > 0.25:
                alerts.append(f"INPUT DRIFT on {name} (PSI {score:.2f})")
        if psi(self.train_scores, live_scores) > 0.25:
            alerts.append("PREDICTION DRIFT: the score distribution has shifted")
        null_rate = np.mean([np.isnan(v).mean() for v in live_features.values()])
        if null_rate > 0.01:
            alerts.append(f"FEATURE PIPELINE broken: {null_rate:.1%} nulls")
        return alerts

# ── 6. SERVING: pick the simplest thing that meets the requirement ──────
#   BATCH     - score every customer nightly into a table; the app reads a row.
#               Simple, cheap, debuggable. Correct for churn, LTV, segmentation.
#   REAL TIME - a service with a p99 latency budget; needed for fraud, ranking,
#               ads. Costs a feature store, a cache and an on-call rota.
#   Do not build real-time serving for a prediction that changes daily.

# ── 7. ROLLOUT, in the order that limits blast radius ───────────────────
#   shadow (score live traffic, act on nothing, compare) ->
#   canary (1% of users) -> A/B (50/50 on the BUSINESS metric) -> full ->
#   and keep the previous model deployable with a one-line rollback.
'''),
          example="The skew failure in one sentence: training computed 'days since signup' in UTC and the serving code used local time, so every prediction near midnight used a feature one day off. Offline AUC 0.87, online performance barely above the old rules engine, and no error in any log. Shared feature code, or a feature store, is the structural fix - and mentioning it unprompted marks you as someone who has shipped.",
          pitfalls="Optimising the offline metric and never checking the business metric; no monitoring, so degradation is discovered by a customer complaint; retraining automatically on data the model itself influenced (a feedback loop - a fraud model that blocks transactions never sees whether they were fraudulent); no rollback path; building real-time infrastructure for a batch problem.",
          followups="'How often would you retrain?' As often as the data drifts - monitor PSI and retrain on a trigger, with a scheduled floor; the answer 'weekly' with no justification is weak. 'How do you know the new model is better?' A shadow comparison on identical traffic, then an A/B test on the business metric with a pre-registered sample size."),

        Q("ml_concepts", "A/B testing an ML model (and the statistics you must get right)",
          "Offline metrics tell you whether the model ranks better; only an experiment tells you whether the PRODUCT got better, and they disagree more often than people expect. THE SETUP: randomly assign users (not requests - the same user must get a consistent experience, or you cannot attribute anything) to control and treatment, run both for a pre-decided duration, and compare ONE pre-registered primary metric plus a small set of guardrails. THE STATISTICS YOU MUST HANDLE. (1) SAMPLE SIZE, computed BEFORE you start from the baseline rate, the minimum effect worth detecting, and the power you want (usually 80%) - halving the detectable effect quadruples the sample needed, which is the calculation that tells you an experiment is not worth running. (2) PEEKING: checking daily and stopping when it looks significant inflates the false-positive rate dramatically, because you get a fresh chance to be fooled every time you look; either fix the duration in advance or use a sequential test designed for continuous monitoring. (3) MULTIPLE COMPARISONS: testing twenty metrics at p<0.05 makes about one spurious 'win' by construction - hence one primary metric, with Bonferroni or false-discovery-rate control on the rest. (4) NOVELTY AND PRIMACY EFFECTS: a change often looks good in week one purely because it is new, so run at least one or two full weekly cycles. (5) SANITY CHECKS FIRST - a sample ratio mismatch (you asked for 50/50 and got 48/52) means the assignment or logging is broken and the result is not interpretable at all. THE ML-SPECIFIC WRINKLES: interference (a recommender in treatment can change what control users see through shared inventory), delayed feedback (a conversion may take days, so a short test undercounts it), and the guardrails that matter as much as the win - latency, error rate, and the metric the change might quietly cannibalise.",
          ["ml", "ab-testing", "experimentation", "statistics", "production", "evaluation"],
          difficulty="Hard",
          frequency="Very commonly asked at Amazon and Google for applied-ML and data-science roles.",
          mnemonic="Randomise by USER, pre-register ONE primary metric plus guardrails, compute the sample size BEFORE starting, do not peek, check for sample ratio mismatch first, and run at least a full week to survive novelty effects.",
          code=_c('''
import numpy as np
from scipy import stats

# ── 1. Sample size, computed BEFORE the experiment ──────────────────────
def sample_size_per_arm(baseline_rate, min_detectable_lift, alpha=0.05, power=0.8):
    """How many users per arm to detect a relative lift with the given power."""
    p1 = baseline_rate
    p2 = baseline_rate * (1 + min_detectable_lift)
    p_bar = (p1 + p2) / 2
    z_a = stats.norm.ppf(1 - alpha / 2)          # two-sided
    z_b = stats.norm.ppf(power)
    n = ((z_a * np.sqrt(2 * p_bar * (1 - p_bar)) +
          z_b * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (p2 - p1) ** 2
    return int(np.ceil(n))

sample_size_per_arm(0.05, 0.10)   # 5% baseline, detect a 10% relative lift
                                  # -> ~31,000 users PER ARM
sample_size_per_arm(0.05, 0.05)   # halve the effect -> ~4x the users (~124,000)
# This calculation is what tells you an experiment is not worth running.

# ── 2. Sanity check FIRST: sample ratio mismatch ────────────────────────
def srm_check(n_control, n_treatment, expected_split=0.5):
    """A 50/50 assignment that lands at 48/52 on large n is a BUG, not luck.
    If this fails, stop - the result cannot be interpreted."""
    total = n_control + n_treatment
    expected = [total * expected_split, total * (1 - expected_split)]
    chi2, p = stats.chisquare([n_control, n_treatment], expected)
    return {"p_value": float(p), "healthy": p > 0.01}

srm_check(48_000, 52_000)      # p is tiny -> the assignment or logging is broken

# ── 3. The test itself ──────────────────────────────────────────────────
def two_proportion_test(conv_c, n_c, conv_t, n_t):
    p_c, p_t = conv_c / n_c, conv_t / n_t
    p_pool = (conv_c + conv_t) / (n_c + n_t)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
    z = (p_t - p_c) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    # A confidence interval on the DIFFERENCE is more useful than the p-value:
    se_diff = np.sqrt(p_c*(1-p_c)/n_c + p_t*(1-p_t)/n_t)
    ci = (p_t - p_c - 1.96 * se_diff, p_t - p_c + 1.96 * se_diff)
    return {"control": p_c, "treatment": p_t,
            "relative_lift": (p_t - p_c) / p_c, "p_value": float(p_value),
            "ci_95": ci}

two_proportion_test(1500, 30_000, 1650, 30_000)   # 5.0% -> 5.5%, +10% relative

# ── 4. Guardrails: a win that breaks something else is not a win ────────
GUARDRAILS = {
    "p99_latency_ms":  ("must not increase by more than 10%", "critical"),
    "error_rate":      ("must not increase at all",           "critical"),
    "unsubscribe_rate":("must not increase",                  "important"),
    "revenue_per_user":("must not decrease",                  "critical"),
}
# A recommender that lifts click-through 8% while adding 200ms of latency and
# raising unsubscribes is a loss. Decide the guardrails BEFORE you see results.

# ── 5. Peeking, quantified ──────────────────────────────────────────────
# Checking once at alpha=0.05 gives a 5% false-positive rate. Checking daily for
# two weeks and stopping at the first significant result pushes it past 20%.
# Fix the duration in advance, or use a sequential/always-valid test.
'''),
          example="The classic disagreement: a new ranking model improves offline NDCG by 4%, and the A/B test shows flat clicks and a 3% drop in sessions. Investigation finds the model favours long-form content that takes longer to consume, so users see fewer items per session. The offline metric measured ranking quality; the experiment measured the product. This is precisely why shipping decisions are made online, and it is a great story to have ready.",
          pitfalls="Randomising by request rather than by user; peeking and stopping early; no pre-registered primary metric, so you go hunting for a winner among twenty; ignoring a sample ratio mismatch; running for three days and missing the weekday/weekend cycle; treating a statistically significant but tiny lift as worth the added complexity of a new model.",
          followups="'How would you shorten the experiment?' Reduce variance with CUPED (use pre-experiment behaviour as a covariate), or pick a more sensitive primary metric that is still aligned with the goal. 'What if you cannot randomise?' Switchback tests for marketplace effects, geo-based splits, or a difference-in-differences quasi-experiment - each weaker, and you should say so."),

        Q("ml_concepts", "Why gradient-boosted trees still beat deep learning on tabular data",
          "A question that is being asked more and more, because the honest answer shows judgement rather than fashion. THE FACT: on typical tabular problems - a few thousand to a few million rows, mixed numeric and categorical columns, heterogeneous scales - gradient-boosted tree ensembles (XGBoost, LightGBM, CatBoost) usually match or beat neural networks, with far less tuning, and this holds up across published benchmark studies. THE REASONS, and each is worth a sentence. (1) INDUCTIVE BIAS: trees split on thresholds, so they naturally model the piecewise-constant, non-smooth relationships tabular data is full of ('risk jumps at age 25 and again at 65'). Neural networks are biased toward smooth functions and have to spend capacity learning the jumps. (2) SCALE AND MONOTONE INVARIANCE: trees care only about the ORDER of a feature's values, so they need no normalisation and are untroubled by skew, outliers or a log-vs-linear encoding - three of the most common sources of neural-network trouble. (3) UNINFORMATIVE FEATURES: trees simply never split on them; a dense network must learn to zero out their weights, which costs data. (4) MISSING VALUES are handled natively by learning a default direction at each split. (5) DATA EFFICIENCY: deep learning's advantage comes from learning representations, which needs lots of data and structure to exploit - and tabular columns carry no spatial or sequential structure to exploit. WHEN NEURAL NETWORKS DO WIN ON TABULAR-ISH DATA: very high-cardinality categoricals where learned embeddings beat one-hot encoding, multi-modal problems mixing text or images with columns, multi-task settings sharing a representation, and genuinely huge datasets. THE INTERVIEW-SAFE POSITION: start with a gradient-boosted baseline on any tabular problem, and justify moving to deep learning with a measured gain rather than a preference.",
          ["ml", "gradient-boosting", "xgboost", "tabular", "deep-learning", "model-selection"],
          difficulty="Medium",
          frequency="Increasingly asked - a good discriminator between fashion-following and judgement.",
          mnemonic="Tabular data is non-smooth, mixed-scale and full of junk columns - exactly what TREES are built for and exactly what neural nets must learn the hard way. Start with LightGBM/XGBoost; earn the right to use deep learning with a measured gain.",
          code=_c('''
import numpy as np
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(0)
n = 5000
# A realistic tabular mix: wildly different scales, a threshold effect,
# a skewed column, and 15 pure-noise features.
age     = rng.integers(18, 90, n)
income  = rng.lognormal(10, 1, n)                 # heavily skewed
noise   = rng.normal(size=(n, 15))                # 15 useless columns
y = ((age > 65) | (income > 60_000)).astype(int)  # a SHARP threshold rule
y = np.where(rng.random(n) < 0.05, 1 - y, y)      # 5% label noise
X = np.c_[age, income, noise]

# Trees: no scaling, no tuning, thresholds are native.
gbdt = cross_val_score(HistGradientBoostingClassifier(), X, y, cv=5).mean()

# Neural net: needs scaling, and must APPROXIMATE the step function with a
# smooth one while also learning to ignore 15 noise features.
mlp = cross_val_score(
    make_pipeline(StandardScaler(), MLPClassifier((64, 32), max_iter=500)),
    X, y, cv=5).mean()

print(round(gbdt, 3), round(mlp, 3))    # GBDT typically ahead, with zero tuning

# ── Where trees are structurally advantaged ─────────────────────────────
# 1. THRESHOLDS      : "age > 65" is one split; a network approximates the step
#                      with several smooth units and never gets it exactly.
# 2. SCALE INVARIANCE: income in euros or in log-euros gives an IDENTICAL tree,
#                      because only the ORDER of values matters.
# 3. NOISE FEATURES  : never selected for a split; a dense layer must learn to
#                      zero 15 sets of weights, which costs data.
# 4. MISSING VALUES  : LightGBM/XGBoost learn a default branch per split.

# ── The practical starting kit for any tabular problem ──────────────────
# import lightgbm as lgb
# model = lgb.LGBMClassifier(
#     n_estimators=2000, learning_rate=0.03,     # low LR + early stopping
#     num_leaves=31, min_child_samples=20,
#     subsample=0.8, colsample_bytree=0.8,       # bagging = regularisation
#     reg_lambda=1.0)
# model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)],
#           callbacks=[lgb.early_stopping(100)])  # let validation pick the size

# WHEN A NEURAL NET IS THE RIGHT CALL ON TABULAR DATA:
#   - very high-cardinality categoricals (millions of user or item ids) where
#     learned EMBEDDINGS beat one-hot encoding outright
#   - text or images alongside the columns (one model, several modalities)
#   - multi-task learning sharing a representation across related targets
#   - tens of millions of rows, where representation learning finally pays
'''),
          example="Boosting's regularisation levers are worth knowing by name because they are what tuning actually means here: a low learning rate with many trees and early stopping (the single most effective combination), subsample and colsample (bagging, which also decorrelates the trees), min_child_samples (leaf size floor), and L1/L2 on the leaf weights. Tuning depth alone, which is what most people do first, is rarely where the gain is.",
          pitfalls="Reaching for deep learning because it is more impressive; not using early stopping with boosting, so the ensemble overfits; one-hot encoding a 10,000-category column for a tree (use target or ordinal encoding, or CatBoost's native handling); comparing an untuned tree model against a heavily tuned network and drawing a conclusion; ignoring that boosting is sequential and therefore harder to parallelise than a random forest.",
          followups="'Bagging or boosting?' Bagging (random forest) trains trees independently on bootstrap samples to reduce VARIANCE; boosting trains them sequentially, each correcting the previous one's errors, reducing BIAS - which is also why boosting overfits more readily and needs early stopping. 'What does CatBoost add?' Ordered target statistics for categoricals, which avoids the target leakage naive target encoding causes."),
    ]

    return entries
