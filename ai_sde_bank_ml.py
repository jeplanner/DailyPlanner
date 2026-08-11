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
              r"""1. THE GOAL - the straight line that comes closest to all the points.

You have points scattered on a graph and you want one straight line that summarises them.

    y
    |                                  .
    |                            .   /
    |                        . /  .
    |                    /  .
    |              .  /
    |          /   .
    |     /  .
    +--------------------------------- x

"Closest" needs a definition, and the choice is not obvious. Measure each point's VERTICAL
distance from the line - the error - then square each one and add them up. The best line is
the one making that total smallest.

    error at a point = actual y  -  the line's y at that x
    total            = the sum of those errors, SQUARED

Why squared rather than absolute? Two reasons, and both are worth saying out loud because
this is a common follow-up:

  - IT PUNISHES LARGE ERRORS MUCH HARDER. One error of 10 counts as 100, while ten errors
    of 1 count as 10 in total. If a single big miss is worse than several small ones - and
    for most predictions it is - squaring encodes that.
  - IT IS DIFFERENTIABLE EVERYWHERE. The absolute-value function has a corner at zero;
    squaring is smooth. That smoothness is what gives a clean formula for the answer and
    lets gradient descent work without special cases.

The model itself:

    y  =  w0  +  w1 x1  +  w2 x2  +  ...  +  wn xn

w0 is the intercept - the prediction when every feature is zero. Each wi says how much y
moves per unit of that feature. That is all a linear model is, and its plainness is exactly
why it survives: you can read the coefficients and say what the model believes.

WHAT THIS ENTRY OWNS: the model, the two ways to solve it, and the ASSUMPTIONS - which is
what a good interviewer actually probes. Its sibling "LOGISTIC REGRESSION" owns what changes
when the target is a class rather than a number, and "HOW GRADIENT DESCENT WORKS" owns the
optimisation loop referenced below.""",
              r"""2. THE INTUITION - two roads to the same answer.

The loss surface for linear regression with squared error is a BOWL. Not a landscape with
hills and valleys - a single smooth bowl with exactly one lowest point:

    loss
      |  \                             /
      |    \                         /
      |      \                     /
      |        \                 /
      |           \___________ /
      +-------------------------------> the weight
                       ^
                 one global minimum, and no other flat spot anywhere

This shape is called CONVEX, and it is a genuinely nice property worth stating in an
interview: THERE ARE NO LOCAL MINIMA TO GET STUCK IN. Whatever route you take downhill, you
arrive at the same place. Most of machine learning does not have this guarantee; linear
regression does.

Because the bowl is smooth and has one bottom, there are two ways to reach it:

    THE NORMAL EQUATION - solve for the bottom directly.

        w = (X-transpose X)-inverse X-transpose y

        One calculation, exact answer, no iteration. It works by setting the slope to zero
        and solving. The catch is the matrix inverse: inverting an n-by-n matrix costs about
        n-cubed operations, where n is the number of FEATURES - not rows.

    GRADIENT DESCENT - walk down the bowl.

        Start anywhere, compute the slope, step downhill, repeat.

        Each step costs about (rows x features), and you need many steps. But nothing is
        inverted, so it scales to enormous data and works when the data arrives in a stream.

Both land at the same point, because there is only one bottom. The choice is purely
practical, and section 9 does the arithmetic that decides it - with 50 features the direct
solve is instantaneous, and with 100,000 features it would take about twelve days.""",
              r"""3. EVERY TERM, defined the first time you meet it.

FEATURE / PREDICTOR / INDEPENDENT VARIABLE (x). An input column - size, age, temperature.

TARGET / RESPONSE / DEPENDENT VARIABLE (y). What you are predicting. A NUMBER here, which is
what makes this regression rather than classification.

COEFFICIENT / WEIGHT (w). How much the prediction moves per unit of a feature.

INTERCEPT / BIAS (w0). The prediction when all features are zero. Often meaningless on its
own - nobody has a house of zero square metres - but it positions the line correctly.

RESIDUAL. Actual minus predicted, for one point. The vertical gap. Residuals are the raw
material of every diagnostic in section 8.

MEAN SQUARED ERROR (MSE). The average of the squared residuals. The thing being minimised.

ORDINARY LEAST SQUARES (OLS). The name for fitting a linear model by minimising squared
error. "Least squares" is literally the description.

CONVEX. Bowl-shaped, with exactly one minimum. Guarantees any downhill route reaches the
global optimum.

NORMAL EQUATION. The closed-form solution. "Closed form" means a direct formula rather than
an iterative search.

PSEUDOINVERSE (pinv). A generalisation of the matrix inverse that still returns an answer
when the matrix is singular - which happens when two feature columns are perfectly
correlated. Using pinv rather than inv is why the code below does not crash on duplicated
columns.

R-SQUARED. The share of the target's variance the model explains. 1.0 is perfect, 0 is no
better than always predicting the mean, and negative is worse than the mean.

HOMOSCEDASTICITY. Constant error variance - the spread of residuals is the same everywhere.
Its opposite, HETEROSCEDASTICITY, is residuals fanning out as predictions grow.

MULTICOLLINEARITY. Features that are strongly correlated with each other. Predictions stay
fine; the individual coefficients become unstable and uninterpretable.

VIF (VARIANCE INFLATION FACTOR). A per-feature number measuring how well the OTHER features
predict it. Above 5 to 10 means that coefficient should not be interpreted.

RESIDUAL PLOT. Residuals plotted against predictions. The single most informative diagnostic
here, and better than any summary number.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1 - THE MOST-ASKED FOLLOW-UP: MULTICOLLINEARITY MAKES COEFFICIENTS MEANINGLESS WHILE
PREDICTIONS STAY FINE.

Predict house price from SIZE IN SQUARE METRES and NUMBER OF ROOMS. These are strongly
correlated - bigger houses have more rooms. Fit it twice on slightly different samples:

    sample A:   price = 200 x size  -  5,000 x rooms  + ...
    sample B:   price =  -50 x size + 30,000 x rooms  + ...

Both predict well. Both are, as coefficient statements, absurd - sample A says an extra room
LOWERS the price by 5,000, sample B says an extra square metre lowers it by 50.

Why it happens: the model only needs the COMBINATION to be right. Since size and rooms carry
nearly the same information, a large positive weight on one can be cancelled by a large
negative weight on the other, and infinitely many such pairs fit almost equally well. The
solver picks one essentially arbitrarily, and a small change in the data picks a different
one.

THE DISTINCTION THAT MATTERS: if you only need PREDICTIONS, multicollinearity is not a
problem. If anyone will READ the coefficients - which is the whole reason to use a linear
model in medicine, credit or policy - it is fatal. Check VIF, and drop or combine the
offending features.

TRAP 2: interpreting the intercept when zero is impossible. "A house of zero square metres
costs 45,000" is not a finding. The intercept positions the line; it is rarely a statement
about the world.

TRAP 3: confusing correlation with causation via the coefficients. A coefficient is "the
expected change in y per unit of this feature, HOLDING THE OTHERS FIXED". It is not a causal
claim, and holding-the-others-fixed may be physically impossible when features are linked.

TRAP 4: relying on R-squared to compare models. It NEVER DECREASES when you add a feature -
add a column of random noise and R-squared goes up. Use adjusted R-squared, or judge on
held-out data.

TRAP 5: ignoring the residual plot. Every assumption failure is visible there and invisible
in the summary numbers. A model with excellent R-squared can have residuals that form a
clear curve, which means the relationship is not linear and the model is systematically
wrong in a pattern you could fix.

TRAP 6: applying it to time series with a random train/test split. The independence-of-errors
assumption is violated - today's error is related to yesterday's - so the model's apparent
accuracy is inflated. Split by time.

TRAP 7: forgetting outliers move the line hard. Squared error means one point ten units away
contributes as much as a hundred points one unit away. A single bad row can visibly tilt the
whole fit, which is the cost of choosing squares over absolutes.""",
              r"""5. THE NAIVE VERSION FIRST, THEN THE REAL ONE.

THE NAIVE VERSION - guess a line and adjust it by eye.

Draw a line that looks about right, check whether it seems close, nudge it. This is exactly
what least squares automates, and stating it makes the next question obvious: what does
"close" mean, precisely enough for a computer?

THE DEFINITION THAT MAKES IT SOLVABLE: minimise the SUM OF SQUARED VERTICAL DISTANCES.

Three choices are buried in that sentence and each is worth defending:

  - VERTICAL distances, not perpendicular. You are predicting y FROM x, so error means being
    wrong about y. (Perpendicular distance gives a different technique, total least squares,
    used when both variables have measurement error.)
  - SQUARED rather than absolute. Punishes large errors harder, and is differentiable
    everywhere so a closed form exists. The cost is sensitivity to outliers - see trap 7.
    Absolute error gives median-like behaviour and needs an iterative solver.
  - SUMMED over all points, so every point has a say.

WHY THERE IS A FORMULA AT ALL - the derivation, briefly, because it explains both solvers.

At the bottom of a smooth bowl the slope is zero in every direction. So write down the
derivative of the total squared error with respect to each weight, set all of them to zero,
and solve the resulting system. In matrix form that system is:

    X-transpose X w  =  X-transpose y

and solving for w gives the normal equation. It is not magic - it is "the slope is zero at
the minimum", written for many variables at once.

TWO SOLVERS, AND THE ARITHMETIC THAT CHOOSES BETWEEN THEM:

    NORMAL EQUATION
        cost: about n-cubed for the inverse, plus m x n-squared to build the matrix, where m
        is rows and n is FEATURES.
        exact, one shot, no hyperparameters, no learning rate to tune.
        n = 50:       51-cubed is about 133,000 operations. Instantaneous.
        n = 1,000:    1 billion operations. A second or two.
        n = 100,000:  10-to-the-15 operations. At a billion operations a second, about
                      TWELVE DAYS.

    GRADIENT DESCENT
        cost: about m x n per step, times the number of steps.
        m = 10 million, n = 100,000, 1,000 steps: large but entirely parallelisable, and it
        never builds an n-by-n matrix, so memory stays manageable.
        needs a learning rate; the sibling entry covers choosing one.

THE RULE: the crossover is driven by the number of FEATURES, not rows. Millions of rows with
50 features is a job for the normal equation. Ten thousand rows with 100,000 features is not.

WHY BOTH REACH THE SAME ANSWER: convexity. One bowl, one bottom. This is not true once you
add a sigmoid - see the logistic sibling, where the choice of loss becomes load-bearing for
exactly this reason.

THE UPGRADE PATH BEYOND PLAIN OLS:
    correlated features or overfitting  ->  add L2 (Ridge). It also makes X-transpose X
                                            invertible again, which is a second reason to
                                            reach for it.
    many useless features               ->  add L1 (Lasso), for sparsity.
    a curved relationship               ->  add polynomial or interaction terms. The model is
                                            still LINEAR IN ITS WEIGHTS, which is all that
                                            "linear model" requires - a common point of
                                            confusion.""",
              r"""6. HOW IT WORKS - the steps, in plain English.

The one sentence that holds the whole idea: FIND THE WEIGHTS THAT MAKE THE SUM OF SQUARED
VERTICAL DISTANCES SMALLEST - EITHER BY SOLVING DIRECTLY FOR WHERE THE SLOPE IS ZERO, OR BY
WALKING DOWNHILL UNTIL YOU REACH THE BOTTOM OF THE BOWL.

THE NORMAL EQUATION HAS NO LOOP AT ALL - it is a single calculation, which is its main
attraction. GRADIENT DESCENT does loop, and here is what governs it:

  - Each pass computes predictions for every row, measures how wrong they are, and nudges
    every weight.
  - Because the surface is CONVEX, every pass strictly improves the loss provided the
    learning rate is below the stability threshold - there is no local minimum to fall into.
  - WHAT MAKES IT STOP: a fixed number of epochs, or the loss changing by less than some
    tolerance between passes. The code below uses the first, which is simplest and always
    terminates.
  - WHAT MAKES IT FAIL: a learning rate above the stability threshold, in which case the loss
    increases every pass and runs to infinity. The gradient descent sibling computes that
    threshold.

THE STEPS:

  1. PUT THE DATA IN A MATRIX - one row per observation, one column per feature.

  2. PREPEND A COLUMN OF ONES. This is the trick that lets the intercept be treated as just
     another weight: a feature that is always 1 has a weight that is added to every
     prediction, which is exactly what an intercept is. It saves handling it separately
     everywhere.

  3. SCALE THE FEATURES if you are using gradient descent. Features on wildly different
     scales make the bowl a long thin ravine, and any learning rate safe for the steep
     direction crawls along the shallow one. The normal equation does not care.

  4. CHOOSE THE SOLVER by the number of FEATURES: up to a few thousand, the normal equation;
     beyond that, or for streaming data, gradient descent.

  5a. NORMAL EQUATION: multiply the data matrix by its own transpose, invert that, and
      multiply through by the transpose times the targets. One shot. Use the PSEUDOINVERSE,
      so perfectly correlated columns give an answer instead of an error.

  5b. GRADIENT DESCENT: start every weight at zero, then repeatedly compute predictions, take
      the average of (prediction minus actual) weighted by each feature, and step every weight
      against it.

  6. CHECK THE RESIDUALS. Plot residual against prediction. This is the step people skip and
     it is where every assumption failure becomes visible - a curve means you need a
     non-linear term, a widening cone means the error variance is not constant.

  7. CHECK VIF before interpreting any coefficient. Above 5 to 10 and that number is not
     a finding.

  8. REPORT R-SQUARED WITH CARE, on held-out data, knowing it never decreases when features
     are added.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

Imagine a long straight stick and a board with nails hammered into it at various heights. You
want to lay the stick across the board so it sits as close as possible to all the nails at
once.

Now attach a spring from each nail straight up or down to the stick. Each spring pulls the
stick toward its nail, and a spring pulls harder the further it is stretched - twice as far
means twice the pull.

Let go, and the stick settles. Where it settles is the least-squares line.

That is not an analogy; it is the same arithmetic. The energy stored in a stretched spring
grows with the SQUARE of how far it is stretched, and the stick comes to rest where the total
energy is smallest - which is exactly where the sum of squared distances is smallest. The
reason large errors count so heavily is the same reason a spring stretched twice as far pulls
twice as hard.

Two consequences fall straight out of the picture.

One nail far from the rest will visibly tilt the whole stick, because its spring is stretched
so much further than the others. That is the outlier sensitivity, and it is inherent to
choosing springs rather than something gentler.

And if two nails are hammered in almost the same place, they pull almost identically. You
cannot tell from the resting position how much of the pull came from each - and that is
multicollinearity. The stick sits in the right place; the question of which nail did the work
has no stable answer.

The last thing you would do is look at how the stick sits relative to each nail - some above,
some below. If the leftovers scatter with no pattern, a straight stick was the right shape. If
they curve - low at both ends and high in the middle - then the nails lie on a curve and no
straight stick will ever fit, however carefully you position it.""",
              r"""8. THE CODE, LINE BY LINE, in the real variable names.

    import numpy as np

    def fit_normal_equation(X, y):

X is the feature matrix (rows by features); y is the vector of targets. Returns the weights,
intercept first. Neither input is modified.

        X_b = np.c_[np.ones(len(X)), X]                    # prepend the intercept

np.c_ concatenates by COLUMN. This puts a column of 1s at the front, so X_b has one more
column than X. The reason is step 2 of section 6: a feature that is always 1 turns the
intercept into an ordinary weight, so the formula below handles it with no special case. The
name X_b is conventional - X with the bias column.

        return np.linalg.pinv(X_b.T @ X_b) @ X_b.T @ y

The normal equation, read right to left: X_b.T @ y correlates each feature with the target;
X_b.T @ X_b captures how the features relate to each other; and the inverse of the second
applied to the first is the answer.

The important detail is PINV RATHER THAN INV. If two columns are perfectly correlated -
duplicated by a data pipeline, or a one-hot encoding with every level kept - then X_b.T @ X_b
is SINGULAR and has no inverse, so np.linalg.inv raises. pinv (the pseudoinverse) returns a
valid answer anyway, choosing the minimum-norm solution among the infinitely many that fit
equally well. It turns a crash into a usable result, at the cost of the coefficients being
one arbitrary choice from many - which is trap 1 again.

    def fit_gradient_descent(X, y, lr=0.01, epochs=1000):

The iterative alternative. lr is the step size, epochs the number of passes - both
hyperparameters the normal equation does not need.

        X_b = np.c_[np.ones(len(X)), X]
        m, n = X_b.shape

m is the number of rows, n the number of columns INCLUDING the intercept. m is needed to
average the gradient; n to size the weight vector.

        w = np.zeros(n)

Start every weight at zero. For linear regression this is safe - the surface is convex, so
the starting point cannot change where you end up, only how long it takes. (In a neural
network zero initialisation is a bug, because every neuron would receive identical gradients
forever. Different situation, same-looking line of code.)

        for _ in range(epochs):

A fixed trip count. This is what guarantees termination: it is a sweep, not a search for
convergence.

            preds = X_b @ w

One matrix multiply gives the prediction for every row at once.

            grad = (2 / m) * X_b.T @ (preds - y)           # d/dw of MSE

The gradient, and it is worth unpacking. (preds - y) is the residual for each row. Multiplying
by X_b.T weights each residual by each feature's value - so a feature that was large where the
error was large gets a large gradient, which is exactly the credit assignment you want. The
2 comes from differentiating the square; dividing by m averages over rows so the step size
does not depend on how much data you have.

            w -= lr * grad

The update from the gradient descent sibling: step against the gradient. Every weight moves
simultaneously.

        return w

After the fixed number of epochs. Note the function does NOT check whether it converged - with
a bad learning rate it will happily return diverged garbage, which is why watching the loss
matters.

    def r_squared(y, y_hat):
        ss_res = ((y - y_hat) ** 2).sum()

The squared error the model leaves behind.

        ss_tot = ((y - y.mean()) ** 2).sum()

The squared error of the DUMBEST reasonable model - always predicting the mean. This is the
baseline R-squared measures against.

        return 1 - ss_res / ss_tot        # 1.0 = perfect, 0.0 = no better than mean

If the model's error equals the mean-model's error, the ratio is 1 and R-squared is 0. If the
model is perfect, ss_res is 0 and R-squared is 1. If the model is WORSE than predicting the
mean, the ratio exceeds 1 and R-squared goes NEGATIVE - possible, and a useful alarm.

    def vif(X):

Variance Inflation Factor - the multicollinearity check.

        for j in range(X.shape[1]):
            others = np.delete(X, j, axis=1)
            w = fit_normal_equation(others, X[:, j])

For each feature in turn, try to predict THAT FEATURE from all the others. This is the whole
idea: if the other features can already reconstruct this one, it carries no independent
information and its coefficient cannot be pinned down.

            out.append(1 / max(1e-12, 1 - r_squared(X[:, j], pred)))

VIF is 1 / (1 - R-squared of that regression). If the others explain 80% of this feature, that
is 1 / 0.2 = 5. If they explain 99%, it is 1 / 0.01 = 100. The max(1e-12, ...) prevents a
division by zero when a feature is perfectly predicted by the others - which would otherwise
be VIF of infinity, and is itself the strongest possible warning.

    RULE OF THUMB: VIF above 5 to 10 means do not interpret that coefficient.""",
              r"""9. TRACED WITH REAL NUMBERS.

FITTING A LINE BY HAND on three points: (1, 2), (2, 4), (3, 5).

    A GUESS FIRST, so the loss is concrete. Try w = 1, b = 1, meaning y = x + 1:

        x=1: predicted 2, actual 2  ->  residual  0
        x=2: predicted 3, actual 4  ->  residual  1
        x=3: predicted 4, actual 5  ->  residual  1

        MSE = (0 + 1 + 1) / 3 = 0.6667

    NOW THE LEAST-SQUARES ANSWER.

        x-mean = (1 + 2 + 3) / 3 = 2
        y-mean = (2 + 4 + 5) / 3 = 3.6667

        the slope is the sum of (x - x-mean)(y - y-mean) divided by the sum of
        (x - x-mean) squared:

            numerator   = (1-2)(2-3.6667) + (2-2)(4-3.6667) + (3-2)(5-3.6667)
                        = (-1)(-1.6667) + 0 + (1)(1.3333)
                        = 1.6667 + 1.3333 = 3.0

            denominator = (-1)^2 + 0^2 + 1^2 = 2

            w = 3.0 / 2 = 1.5

        the intercept keeps the line passing through the means:

            b = 3.6667 - 1.5 x 2 = 0.6667

    CHECK THE FIT:

        x=1: 1.5(1) + 0.6667 = 2.1667,  residual  2 - 2.1667 = -0.1667
        x=2: 1.5(2) + 0.6667 = 3.6667,  residual  4 - 3.6667 =  0.3333
        x=3: 1.5(3) + 0.6667 = 5.1667,  residual  5 - 5.1667 = -0.1667

        MSE = (0.02778 + 0.11111 + 0.02778) / 3 = 0.16667 / 3 = 0.05556

    The guess scored 0.6667; the optimum scores 0.05556 - TWELVE TIMES better. And note the
    residuals sum to almost exactly zero (-0.1667 + 0.3333 - 0.1667 = -0.0001, rounding),
    which is always true when an intercept is fitted: the line passes through the mean of the
    data.

    R-SQUARED for this fit:

        ss_res = 0.16667
        ss_tot = (2-3.6667)^2 + (4-3.6667)^2 + (5-3.6667)^2
               = 2.7778 + 0.1111 + 1.7778 = 4.6667
        R-squared = 1 - 0.16667 / 4.6667 = 1 - 0.0357 = 0.964

    The model explains 96.4% of the variation in y.

THE SOLVER CHOICE, WITH THE ARITHMETIC THAT INVERTS IT.

    The normal equation inverts an (n+1) by (n+1) matrix, costing about n-cubed operations,
    where n is the number of FEATURES. At roughly a billion operations per second:

        n =      50   ->  51^3      =         132,651  ->  instantaneous
        n =     500   ->  501^3     =     125,751,501  ->  about 0.1 seconds
        n =   5,000   ->  5001^3    = 125,075,015,001  ->  about 2 minutes
        n = 100,000   ->  100001^3  = about 10^15      ->  about TWELVE DAYS

    Meanwhile the number of ROWS barely matters to that cost - ten million rows with 50
    features is still instantaneous, because rows only enter when building the matrix, which
    is linear in them.

    SO THE ANSWER INVERTS ON FEATURE COUNT, NOT DATA SIZE:

        10,000 rows,      50 features  ->  normal equation. Exact, instant, no tuning.
        10 million rows,  50 features  ->  STILL the normal equation.
        10,000 rows, 100,000 features  ->  gradient descent. The direct solve would take
                                           nearly a fortnight for a small dataset.

    That is the point worth making in an interview: candidates reach for gradient descent when
    the data is big, but the deciding quantity is the number of features.

THE MULTICOLLINEARITY FAILURE, in coefficients.

    Predicting house price from size (square metres) and rooms, which are 0.9 correlated.
    Two samples from the same population:

        sample A:  price = 45,000 + 200 x size  -  5,000 x rooms
        sample B:  price = 45,000 -  50 x size  + 30,000 x rooms

    For a 100 square metre, 4 room house:

        sample A:  45,000 + 20,000 - 20,000 = 45,000
        sample B:  45,000 -  5,000 + 120,000 = 160,000

    The predictions diverge here because I have written two fits that agree on the training
    cloud and not on this particular point - which is itself the warning. Within the range
    where the data actually lives, both fit well; step outside it and they disagree wildly,
    because they have split the shared signal differently.

    VIF diagnoses it directly. Predict size from rooms alone and suppose it gets R-squared
    0.81. Then VIF = 1 / (1 - 0.81) = 1 / 0.19 = 5.26 - at the threshold, and a signal not to
    interpret either coefficient.""",
              r"""10. THE COSTS IN PLAIN WORDS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT IT COSTS:

  - NORMAL EQUATION: about n-cubed in FEATURES, plus m x n-squared to build the matrix.
    Memory holds an n-by-n matrix. No hyperparameters at all, which is a genuine advantage -
    nothing to tune, nothing to get wrong.
  - GRADIENT DESCENT: about m x n per step. Scales to any size, needs a learning rate, and
    needs the features scaled.
  - PREDICTION: one multiply-and-add per feature. Effectively free, which is why linear models
    remain the choice where latency matters.
  - INTERPRETABILITY: essentially free, and the main reason to use this model at all - as long
    as the multicollinearity check passes.

THE ASSUMPTIONS, and what breaks when each fails - this is what a good interviewer probes:

    LINEARITY. The relationship really is a straight line. Fails as a CURVE in the residual
    plot. Fix with polynomial or interaction terms - the model stays linear in its weights.

    INDEPENDENCE OF ERRORS. One row's error tells you nothing about the next. Violated by time
    series and by repeated measures. Consequence: standard errors and confidence intervals are
    wrong, and a random split inflates apparent accuracy.

    HOMOSCEDASTICITY. Constant error variance. Fails as a WIDENING CONE in the residual plot.
    Consequence: predictions are still unbiased, but confidence intervals are wrong. Often
    fixed by predicting log(y) instead.

    NORMALLY DISTRIBUTED RESIDUALS. Needed for INFERENCE - p-values and confidence intervals -
    not for prediction. Worth saying explicitly, because candidates often claim linear
    regression "requires normally distributed data", which is wrong twice over: it is the
    residuals rather than the data, and only for inference.

    NO SEVERE MULTICOLLINEARITY. Predictions survive it; coefficients do not.

FOLLOW-UPS WORTH HAVING READY:

  - "Why squared error rather than absolute?" Differentiable everywhere so there is a closed
    form, and it punishes large errors harder. The cost is outlier sensitivity; absolute error
    gives a median-like fit and needs an iterative solver.
  - "Normal equation or gradient descent?" Decided by the number of FEATURES. Section 9 has the
    numbers.
  - "What if X-transpose X is not invertible?" Perfectly correlated columns. Use the
    pseudoinverse, drop a column, or add L2 - which makes it invertible again as a side effect,
    and is the tidiest of the three.
  - "Can linear regression fit a curve?" Yes - add x-squared as a feature. "Linear" refers to
    linearity in the WEIGHTS, not in the inputs. This one catches a lot of people.
  - "R-squared went up when I added a feature. Better model?" Not necessarily; it never
    decreases. Use adjusted R-squared or held-out data.

THE #1 MISTAKE: interpreting coefficients without checking for multicollinearity. The model
predicts perfectly well and the individual numbers are close to arbitrary - one sample says a
room adds 30,000 and another says it subtracts 5,000. Since interpretability is the main
reason to choose a linear model, this quietly destroys the thing you came for.

RUNNER-UP: never plotting the residuals, so a curved relationship hides behind a respectable
R-squared.

TAKEAWAY: least squares finds the one line at the bottom of a convex bowl, so any route gets
you there - and the interesting work is not the fitting but the assumptions, especially
whether correlated features have made your coefficients unreadable.""",
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
              r"""1. THE GOAL - a probability, not a number.

You want to predict a CLASS - spam or not, fraud or not, ill or not - and ideally a
probability with it, so downstream decisions can weigh the cost of being wrong.

The obvious idea is to code the classes as 0 and 1 and fit a straight line. It does not work,
and the reasons are concrete:

    a straight line predicts 1.4  ->  a probability of 140%, which is meaningless
    a straight line predicts -0.3 ->  a probability of minus 30%, likewise
    one far-away point tilts the whole line  ->  and tilting the line MOVES THE BOUNDARY,
                                                 so predictions flip for points nowhere near
                                                 the outlier

So keep the linear part - it is interpretable and cheap - and BEND THE OUTPUT so it can only
ever land between 0 and 1:

    p  =  sigma( w . x  +  b )        where   sigma(z) = 1 / (1 + e-to-the-minus-z)

That S-shaped function is the SIGMOID. It takes any number at all, however large or negative,
and returns something strictly between 0 and 1.

Note what has NOT changed: the model is still LINEAR IN ITS INPUTS. Only the output is
squashed. That is why logistic regression is linear regression's classification sibling
rather than a different animal, and why the decision boundary is still a straight line.

WHAT THIS ENTRY OWNS: why the squashing is necessary, why the LOSS must change too - which is
the part most explanations skip and section 5 derives with numbers - and how to read the
coefficients as odds ratios. Its sibling "LINEAR REGRESSION FROM FIRST PRINCIPLES" owns the
underlying linear model and its assumptions; "PRECISION VS RECALL" and "ROC, AUC & CHOOSING A
THRESHOLD" own what to do with the probabilities once you have them.""",
              r"""2. THE INTUITION - the S-curve, and where the boundary lives.

    p
    1.0 |                    ________________
        |                _/
        |              /
    0.5 |- - - - - - -/- - - - - - - - - - -
        |           /
        |        _/
    0.0 |_______/
        +--------------------------------------> z = w.x + b
       -6      -2    0    2       6

Read off a few values so the shape is real:

    sigma(-4) = 0.018        far below the boundary  ->  almost certainly class 0
    sigma(-1) = 0.269
    sigma( 0) = 0.500        exactly on the boundary ->  no information either way
    sigma( 1) = 0.731
    sigma( 4) = 0.982        far above                ->  almost certainly class 1

Three properties that make this the right function:

  - IT NEVER LEAVES (0, 1). Feed it a million and it returns 0.9999...; feed it minus a
    million and it returns 0.0000...1. A probability is guaranteed by construction rather
    than by hoping.
  - IT SATURATES. Far from the boundary the curve flattens, so pushing a point further into
    territory it already occupies barely changes its probability. That is what makes it
    robust to the outlier that would have tilted a straight line.
  - THE DECISION BOUNDARY IS WHERE z = 0, which is w . x + b = 0 - a straight line in two
    dimensions, a plane in three, a hyperplane in general.

That last point is the one to hold on to. The PROBABILITIES curve, but the BOUNDARY is
straight. So logistic regression can separate classes lying on either side of a line, and
cannot separate XOR-shaped data at all - section 4 shows the failure and the fix.

And the flattening has a sting in the tail. Where the curve is flat, its SLOPE is nearly
zero - and a slope of nearly zero means almost no gradient, which means almost no learning.
That fact is what makes the choice of loss function load-bearing rather than cosmetic, and
section 5 works it out with numbers.""",
              r"""3. EVERY TERM, defined the first time you meet it.

BINARY CLASSIFICATION. Predicting one of two classes, coded 0 and 1.

SIGMOID / LOGISTIC FUNCTION. sigma(z) = 1 / (1 + e-to-the-minus-z). Maps any real number into
(0, 1). Its S-shape is where "logistic" comes from.

z / LOGIT / PRE-ACTIVATION. The linear part, w . x + b, before squashing. It can be any
number.

ODDS. Probability divided by its complement: p / (1 - p). A probability of 0.75 is odds of 3 -
"three to one on".

LOG-ODDS. The natural logarithm of the odds. This is exactly what z is, which is the single
most useful fact for interpreting the model: the linear part outputs log-odds, and the sigmoid
converts log-odds back to a probability.

ODDS RATIO. e-to-the-w for a coefficient w. How much the ODDS are MULTIPLIED per unit increase
in that feature. This is what makes the model reportable in medicine and credit.

LOG LOSS / BINARY CROSS-ENTROPY. The loss used here: minus the average of
y log(p) + (1-y) log(1-p). Punishes confident wrong answers enormously.

CONVEX. Bowl-shaped with one minimum. Log loss with a sigmoid is convex; SQUARED ERROR with a
sigmoid is not - which is half the reason for the choice.

DECISION BOUNDARY. The set of points where the model is exactly undecided, p = 0.5, which is
z = 0.

THRESHOLD. The probability above which you act. 0.5 is a default, not a recommendation - it is
a business decision, covered in the ROC sibling.

CALIBRATION. Whether a predicted 0.7 really happens about 70% of the time. Logistic regression
trained with log loss is naturally well calibrated, which is a genuine advantage over many
fancier models.

SOFTMAX REGRESSION / MULTINOMIAL LOGISTIC. The multi-class generalisation - one weight vector
per class, outputs normalised to sum to 1.

ONE-VS-REST. The other multi-class approach: train one binary classifier per class.

NAT. The unit of log loss when using natural logarithms. Predicting 0.99 for something that
was false costs -ln(0.01) = 4.6 nats.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1 - THE ONE IN THE TITLE: fitting a straight line to 0/1 labels.

Predict spam (1) or not (0) from the count of spammy words. Most emails have 5 to 50 such
words, and a straight line through them is roughly sensible in that range. Then one email
arrives with 500.

To keep the squared error down at that far-right point, the line must TILT. But the line is a
single global object - tilting it to accommodate one distant point moves it EVERYWHERE, so
the crossing point where predictions pass 0.5 shifts, and emails in the ordinary 5-to-50 range
that were correctly classified now flip.

A single outlier changed the decisions for points nowhere near it. The sigmoid does not
behave this way: at 500 spammy words it already outputs 0.9999, and pushing it further changes
almost nothing, because the curve is flat there.

TRAP 2 - THE SUBTLE ONE, and a favourite follow-up: USING SQUARED ERROR WITH A SIGMOID.

It seems harmless - you have a probability and a target, so square the difference. Two things
break, and section 5 derives both:

    THE SURFACE IS NO LONGER CONVEX. Squared error composed with a sigmoid produces a loss with
    multiple flat regions and local minima, so gradient descent can stall in a bad one. Log
    loss with a sigmoid is convex - one bowl, one bottom.

    THE GRADIENT VANISHES EXACTLY WHEN THE MODEL IS MOST WRONG. With squared error the gradient
    carries a factor of the sigmoid's slope, which is nearly zero far from the boundary. So a
    confidently wrong prediction - the case you most urgently need to fix - produces almost no
    correction. With log loss that factor cancels exactly and the gradient is simply (p - y),
    which is LARGEST when the model is most wrong. Section 9 puts a number on it: about 203
    times larger at z = -6, and about 11,000 times at z = -10.

TRAP 3: expecting a curved decision boundary. The probabilities curve; the boundary does not.
On XOR-shaped data - positives at (0,0) and (1,1), negatives at (0,1) and (1,0) - no straight
line separates the classes, and logistic regression cannot do better than chance. THE FIX is
to add an INTERACTION FEATURE x1 times x2, after which the data IS linearly separable in the
expanded space. Section 9 gives weights that work.

TRAP 4: reading a coefficient as a change in probability. It is a change in LOG-ODDS. The
effect on probability depends on where you start: moving z from 0 to 1 changes p from 0.500 to
0.731 - 23 points - while moving from 4 to 5 changes it from 0.982 to 0.993, barely 1 point.
Same coefficient, wildly different effect on probability. Report the odds ratio, which is
constant.

TRAP 5: leaving the threshold at 0.5. It is a default in the library, not a claim about your
problem. It is optimal only when the classes are balanced AND the two error types cost the
same.

TRAP 6: regularising the intercept. It sets the base rate of the prediction; shrinking it
toward zero biases everything toward p = 0.5 for no gain. Note the code below explicitly skips
it with grad[1:].

TRAP 7: computing the sigmoid naively. exp of a large positive number overflows. The code
handles it with a branch - see section 8.""",
              r"""5. THE NAIVE VERSION FIRST, THEN THE REAL ONE - WITH THE LOSS DERIVED.

THE NAIVE VERSION: linear regression on 0/1 labels.

Fit a straight line to targets that are 0 or 1, then call the output a probability and
threshold it at 0.5. Trap 1 covers why it fails: unbounded outputs, and outliers that move the
boundary for everyone.

UPGRADE 1 - SQUASH THE OUTPUT. Keep the linear part, pass it through the sigmoid. Now outputs
are always valid probabilities and distant points saturate instead of dominating.

But this creates a NEW problem that most explanations skip, and it is the whole content of
this section.

UPGRADE 2 - CHANGE THE LOSS TOO. Here is why.

    Write z for the linear part and p = sigma(z) for the prediction. The sigmoid's slope has a
    tidy form:

        sigma-prime(z)  =  p (1 - p)

    Now compare the two candidate losses by how hard they push on z when the model is wrong.

    WITH SQUARED ERROR, loss = (p - y)-squared:

        d(loss)/dz  =  2 (p - y) x sigma-prime(z)  =  2 (p - y) x p (1 - p)

        That p(1-p) factor is the problem. It is largest at p = 0.5 (where it equals 0.25) and
        it COLLAPSES toward zero as p approaches 0 or 1.

        Take the worst case: the true label is 1 and the model confidently says 0. At z = -6:

            p               = sigma(-6)      = 0.002473
            p (1 - p)       = 0.002473 x 0.997527 = 0.002467
            (p - y)         = 0.002473 - 1   = -0.997527
            d(loss)/dz      = 2 x (-0.997527) x 0.002467 = -0.004921

        A gradient of 0.005. The model is as wrong as it is possible to be, and it is barely
        being corrected.

    WITH LOG LOSS, loss = -[ y log(p) + (1-y) log(1-p) ]:

        d(loss)/dz  =  p - y

        That is the whole thing. The p(1-p) from the sigmoid's slope CANCELS EXACTLY against
        the 1/(p(1-p)) coming from differentiating the logarithm. At the same point:

            d(loss)/dz  =  0.002473 - 1  =  -0.997527

        A gradient of 0.998 - about 203 TIMES LARGER than squared error's 0.00492, at exactly
        the moment the model most needs to move.

    And it gets more extreme the more confidently wrong the model is. At z = -10:

            squared error:  2 x (-0.9999546) x 0.0000454 = -0.0000908
            log loss:       -0.9999546
            ratio:          about 11,000 times larger

    SO THE CHOICE OF LOSS IS NOT AESTHETIC. Squared error makes the model learn slowest
    precisely where it is most wrong. Log loss makes the correction proportional to the error,
    always.

    THE SECOND REASON: squared error composed with a sigmoid is NON-CONVEX, so there are local
    minima to get stuck in. Log loss with a sigmoid is convex - one bowl, one bottom, the same
    happy property linear regression has.

    THE THIRD REASON, worth mentioning: log loss punishes confident wrongness enormously.
    Predicting 0.99 for something that turns out to be 0 costs -ln(0.01) = 4.6 nats, whereas
    predicting 0.6 for it costs -ln(0.4) = 0.92. Five times the penalty for being confident
    about it - which is exactly the incentive you want, and it is why models trained this way
    come out CALIBRATED.

AND THE ELEGANCE THAT FALLS OUT: because the gradient is (p - y), the update rule is

    gradient  =  X-transpose (p - y) / m

which is IDENTICAL IN FORM to linear regression's. Same code shape, different link function.
That is what choosing cross-entropy buys you, and it generalises: the same cancellation is why
softmax pairs with cross-entropy in every neural network classifier.""",
              r"""6. HOW IT WORKS - the steps, in plain English.

The one sentence that holds the whole idea: COMPUTE A LINEAR SCORE, SQUASH IT THROUGH AN
S-CURVE TO GET A PROBABILITY, AND TRAIN BY MINIMISING LOG LOSS - WHICH IS CHOSEN SO THAT THE
CORRECTION IS LARGEST EXACTLY WHEN THE MODEL IS MOST WRONG.

THERE IS NO CLOSED FORM HERE - and this is a real difference from linear regression worth
stating. The sigmoid makes the equations transcendental, so you cannot set the gradient to zero
and solve. Iteration is mandatory, not merely convenient.

THE LOOP:

  - Each pass computes probabilities for every row, measures (p - y), and nudges every weight.
  - Because log loss with a sigmoid is CONVEX, every pass improves things provided the learning
    rate is sane, and there is no local minimum to fall into.
  - WHAT MAKES IT STOP: a fixed number of epochs, or the loss changing by less than a tolerance.
    The code uses a fixed count, which always terminates.
  - ONE EDGE CASE WORTH KNOWING: if the classes are PERFECTLY SEPARABLE, the weights grow
    without bound - the model keeps getting more confident forever and the loss keeps falling
    toward zero. Regularisation stops this, which is a second reason to use it beyond
    overfitting.

THE STEPS:

  1. PREPEND A COLUMN OF ONES, so the intercept is just another weight - the same trick as in
     linear regression.

  2. SCALE THE FEATURES. Gradient descent is the only option here, so unscaled features make a
     ravine-shaped surface and slow everything down.

  3. START ALL WEIGHTS AT ZERO. Safe here, because the surface is convex - the starting point
     changes only the route, not the destination.

  4. REPEAT for a fixed number of passes:

     a. COMPUTE THE LINEAR SCORE for every row: the weighted sum of its features.

     b. SQUASH each score through the sigmoid to get a probability.

     c. COMPUTE THE ERROR as simply (probability minus label). No sigmoid-slope factor - that
        is what choosing log loss bought you.

     d. TURN THAT INTO A GRADIENT by weighting each row's error by its feature values and
        averaging.

     e. ADD THE REGULARISATION TERM to every weight EXCEPT the intercept.

     f. STEP every weight against the gradient.

  5. TO PREDICT, compute the probability and compare it against a threshold. The threshold is a
     BUSINESS decision - the ROC sibling covers choosing it - and 0.5 is merely the default.

  6. TO INTERPRET, exponentiate each coefficient to get an ODDS RATIO, which is the form a
     non-specialist can actually use.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

Imagine a doctor estimating how likely it is that a patient has a particular condition.

She has several pieces of information - age, a blood measurement, whether a symptom is present
- and she has learned roughly how much each one counts. So she adds up a score: so many points
for each year of age, so many for the blood reading, a lump for the symptom. High score,
worried. Low score, reassured.

But a score is not an answer. Somebody wants a probability, and a raw score can be anything -
minus forty, three hundred. So she needs a way to turn any score into a sensible chance.

The conversion she uses has a particular shape. Around the middle - where the score is
genuinely borderline - a small change in the score moves the probability a lot, because that is
where she is most uncertain and most sensitive to evidence. Out at the extremes it barely moves
at all: once she is at 98% confident, another few points of score takes her to 98.5%, and that
is right. A patient who was already an obvious case does not become more obvious.

That flattening at the extremes is what protects her from one bizarre reading dominating
everything. In the straight-line version, an extreme value would drag her whole scale and make
her rethink ordinary patients too.

Now, how does she LEARN the points in the first place? By being scored on her past predictions,
and the scoring rule matters enormously.

Under a gentle rule, being confidently wrong is barely penalised - and worse, being
confidently wrong teaches her almost nothing, because the rule barely registers it. She would
keep making the same confident mistake.

Under the rule she actually uses, confident wrongness is punished severely, and the correction
she receives is proportional to how wrong she was. Say 99% certain about something that turns
out false, and you get a large, sharp correction. That is exactly the feedback that fixes the
belief, and it is why she ends up not merely accurate but honestly calibrated - when she says
70%, it happens about seven times in ten.

And the useful thing about her score being a simple sum: she can say what each piece
contributed. "Each additional year of age multiplies the odds by 1.05." That sentence is why
this method is still used where a decision has to be explained to a patient, a regulator, or a
court.""",
              r"""8. THE CODE, LINE BY LINE, in the real variable names.

    def sigmoid(z):
        return np.where(z >= 0, 1 / (1 + np.exp(-z)),
                        np.exp(z) / (1 + np.exp(z)))

Two algebraically identical formulas, chosen by sign, and the reason is OVERFLOW. For a large
NEGATIVE z, exp(-z) is exp of a large positive number, which overflows to infinity. So:

    for z >= 0, use 1/(1 + exp(-z)) - here -z is negative, exp(-z) is small, safe.
    for z <  0, use exp(z)/(1 + exp(z)) - here z is negative, exp(z) is small, also safe.

Each branch only ever exponentiates a non-positive number. np.where evaluates both branches and
selects, so the code is written to be safe in the branch that gets used.

    def log_loss(y, p, eps=1e-15):
        p = np.clip(p, eps, 1 - eps)         # never take log(0)

log(0) is minus infinity. If the model ever outputs exactly 0 or exactly 1 - which floating
point rounding will produce for large z - the loss becomes infinite and everything downstream
becomes NaN. Clipping to 1e-15 caps the worst case at -log(1e-15), about 34.5, which is large
enough to punish and finite enough to compute with.

        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

The log loss itself. Read the two terms as a switch: when y is 1 the second term is zero and the
loss is -log(p), so it rewards p being near 1. When y is 0 the first term is zero and the loss is
-log(1-p). Only one term is ever active per row. The leading minus makes it a quantity to
MINIMISE.

    def fit_logistic(X, y, lr=0.1, epochs=2000, l2=0.0):
        X_b = np.c_[np.ones(len(X)), X]
        w = np.zeros(X_b.shape[1])

The intercept column and zero initialisation, exactly as in the linear sibling. Zeros are safe
because the surface is convex.

        for _ in range(epochs):
            p = sigmoid(X_b @ w)

One matrix multiply gives every row's score; the sigmoid turns them all into probabilities.

            grad = X_b.T @ (p - y) / len(y)

THE LINE THAT JUSTIFIES THE WHOLE CHOICE OF LOSS. (p - y) is the raw error per row - no
sigmoid-slope factor anywhere, because it cancelled (section 5). X_b.T weights each row's error
by its feature values, so a feature that was large where the error was large gets a large
gradient. Dividing by len(y) averages over rows.

Compare with linear regression's gradient: X_b.T @ (preds - y) x 2/m. IDENTICAL IN FORM. That is
the elegance cross-entropy buys - the same update code with a different link function.

            grad[1:] += l2 * w[1:]           # regularise weights, never the intercept

The L2 penalty's contribution. The [1:] on both sides is deliberate and is trap 6: position 0
is the intercept, which sets the model's base rate, and shrinking it toward zero would bias
every prediction toward 0.5 for no benefit.

            w -= lr * grad

The standard update from the gradient descent sibling.

        return w

After a fixed epoch count. Note there is no convergence check - with a bad learning rate this
returns diverged weights without complaint.

    odds_ratios = np.exp(w[1:])

THE INTERPRETATION STEP. A coefficient is a change in LOG-odds, which nobody can reason about
directly. Exponentiating converts it to a multiplier on the ODDS. Again [1:] excludes the
intercept, which has no odds-ratio reading. A value of 1.05 for "age" means each extra year
multiplies the odds by 1.05 - a sentence you can say to a non-specialist.

    def predict(X, w, threshold=0.5):
        return (sigmoid(np.c_[np.ones(len(X)), X] @ w) >= threshold).astype(int)

Probability, then compare to the threshold. The default of 0.5 is a convention, not a
recommendation - it is optimal only when the classes are balanced and the two error types cost
the same. Cancer screening lowers it; spam filtering raises it.""",
              r"""9. TRACED WITH REAL NUMBERS.

THE SIGMOID AND ITS SLOPE, tabulated - because the slope column is the whole argument:

        z         p = sigma(z)      slope p(1-p)
      ------      ------------      ------------
       -10          0.0000454        0.0000454
        -6          0.002473         0.002467
        -4          0.017986         0.017663
        -1          0.268941         0.196612
         0          0.500000         0.250000
         1          0.731059         0.196612
         4          0.982014         0.017663

    The slope peaks at 0.25 in the middle and collapses at the extremes. That collapse is what
    kills squared error.

THE GRADIENT COMPARISON, at the worst possible moment - true label y = 1, model says z = -6:

    SQUARED ERROR:
        p          = 0.002473
        (p - y)    = 0.002473 - 1 = -0.997527
        slope      = p(1-p)       =  0.002467
        gradient   = 2 x (-0.997527) x 0.002467  =  -0.004921

    LOG LOSS:
        gradient   = p - y  =  0.002473 - 1  =  -0.997527

    RATIO: 0.997527 / 0.004921  =  about 203 times larger.

    AND AT z = -10, more confidently wrong still:

        squared error:  2 x (-0.9999546) x 0.0000454  =  -0.0000908
        log loss:       -0.9999546
        RATIO:          about 11,000 times larger.

    NOTICE THE DIRECTION OF THE EFFECT. The MORE confidently wrong the model is, the WEAKER
    squared error's correction becomes - 203x behind at z = -6, 11,000x behind at z = -10. It
    learns slowest exactly where it is most wrong. Log loss's correction converges to 1.0, its
    maximum possible value, at the same point.

    That is the derivation to give when asked "why cross-entropy rather than MSE?", and it beats
    saying "because it is convex" - which is also true, and less vivid.

THE COST OF CONFIDENT WRONGNESS, in log loss:

        predicted    true label    loss = -ln(...)
        ---------    ----------    ---------------
        0.99             0          -ln(0.01) = 4.605
        0.90             0          -ln(0.10) = 2.303
        0.60             0          -ln(0.40) = 0.916
        0.50             0          -ln(0.50) = 0.693
        0.10             0          -ln(0.90) = 0.105

    Being 99% sure and wrong costs FIVE TIMES what being 60% sure and wrong costs. That steep
    penalty is what produces calibration - the model learns not to claim more confidence than it
    has.

ODDS RATIOS, worked:

    A credit model gives coefficient 0.7 on debt-to-income ratio.

        odds ratio = e-to-the-0.7 = 2.01

        A one-unit increase in debt-to-income ratio DOUBLES the odds of default.

    Converting to probability, to show why the odds ratio is the right thing to report:

        starting at odds 0.25 (p = 0.20):  new odds 0.503  ->  p = 0.335   (+13.5 points)
        starting at odds 4.00 (p = 0.80):  new odds 8.05   ->  p = 0.890   (+ 9.0 points)

    THE SAME COEFFICIENT MOVES THE PROBABILITY BY DIFFERENT AMOUNTS depending on where you start
    - which is exactly why a coefficient is not a change in probability, and why the odds ratio,
    which IS constant, is the number to report.

THE THRESHOLD AS A BUSINESS DECISION, with numbers:

    A fraud model outputs probabilities. Sweeping the threshold:

        threshold 0.5:  40 frauds caught, 10 missed,  20 false alarms
        threshold 0.3:  47 frauds caught,  3 missed,  90 false alarms

    Lowering it by 0.2 catches 7 more frauds and creates 70 more false alarms. Whether that is a
    good trade is arithmetic on the cost of each - not a modelling question at all. The ROC
    sibling does that arithmetic.

WHAT IT CANNOT DO - XOR, and the fix:

    positives at (0,0) and (1,1);  negatives at (0,1) and (1,0)

        (0,1) N     (1,1) P
             +-----------+
             |           |
             |           |
             +-----------+
        (0,0) P     (1,0) N

    No straight line puts both P's on one side and both N's on the other - the positives are
    diagonally opposite. Logistic regression is at chance here.

    THE FIX: add an interaction feature, the product x1 times x2. Now with weights w1 = -1,
    w2 = -1, w3 = +2 on the product, and b = 0.5:

        (0,0):  0 + 0 + 0 + 0.5        = +0.5   ->  positive   correct
        (1,1): -1 - 1 + 2 + 0.5        = +0.5   ->  positive   correct
        (0,1):  0 - 1 + 0 + 0.5        = -0.5   ->  negative   correct
        (1,0): -1 - 0 + 0 + 0.5        = -0.5   ->  negative   correct

    All four correct. The boundary is still a straight hyperplane - it just lives in the
    three-dimensional space {x1, x2, x1x2} rather than the two-dimensional one. This is the same
    idea a kernel exploits, and it is why "linear model" is less limiting than it sounds.""",
              r"""10. THE COSTS IN PLAIN WORDS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT IT COSTS:

  - TRAINING: no closed form, so it is iterative - about (rows x features) per pass. Cheap by
    any modern standard, and convex so it converges reliably.
  - PREDICTION: one dot product and one exponential. Effectively free, which matters when you
    are scoring millions of requests a second - and is why logistic regression is still running
    in production under a lot of systems that also have a neural network somewhere.
  - INTERPRETABILITY: free, and the main reason it survives. One number per feature, reportable
    as an odds ratio.
  - CALIBRATION: free, because log loss rewards honest probabilities. Many stronger models need
    a separate calibration step to achieve this; logistic regression arrives calibrated.

WHERE IT SITS AMONG THE ALTERNATIVES:
    Use it as the FIRST model and the baseline everything else must beat. If a gradient-boosted
    forest cannot beat it by a meaningful margin, ship the logistic regression - it is faster,
    explainable, and will not surprise you.
    Move on when the boundary is genuinely non-linear and you cannot engineer the features to
    make it linear, or when interactions are numerous and unknown.

FOLLOW-UPS WORTH HAVING READY:

  - "Why not use MSE with a sigmoid?" Two reasons, and give the second one with numbers: the
    surface is non-convex, AND the gradient vanishes exactly when the model is confidently
    wrong - about 203 times weaker at z = -6, 11,000 times at z = -10. Log loss's gradient is
    (p - y), largest when most wrong.
  - "What does a coefficient mean?" A change in LOG-ODDS per unit. Exponentiate for the odds
    ratio, which is the interpretable form. It is not a change in probability - that depends on
    where you start.
  - "Is logistic regression linear?" Linear in the inputs and in the log-odds; the decision
    boundary is a hyperplane. Only the output is bent.
  - "How do you handle more than two classes?" Softmax regression - one weight vector per class,
    outputs normalised to sum to 1 - or one-vs-rest. Softmax is the direct generalisation and
    pairs with cross-entropy for exactly the same gradient-cancellation reason.
  - "What if the classes are perfectly separable?" The weights diverge, growing without bound as
    the model becomes ever more confident. Regularisation fixes it, which is a reason to use it
    beyond overfitting.
  - "How do you deal with imbalanced classes?" Class weights in the loss, or move the threshold.
    Do NOT reach for accuracy as the metric - see the Precision vs Recall sibling.

THE #1 MISTAKE: pairing a sigmoid with squared error. It looks reasonable, it runs, and it
trains badly for a reason that is invisible unless you differentiate it - the correction shrinks
toward nothing precisely when the model is most confidently wrong. The pairing of sigmoid with
cross-entropy is not convention; it is the cancellation that makes the gradient behave.

RUNNER-UP: reporting coefficients as changes in probability rather than odds, which is wrong by
an amount that depends on where the patient or customer started.

TAKEAWAY: keep the linear score, squash it through an S-curve so it is always a probability, and
train with log loss - because that specific pairing cancels the sigmoid's vanishing slope and
makes the correction largest exactly when the model is most wrong.""",
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
          examples=[
              "Gini and entropy computed by hand on the same node. A node holding 6 negatives and 4 positives: p = (0.6, 0.4). Gini = 1 - (0.36 + 0.16) = 0.48. Entropy = -(0.6 * log2 0.6 + 0.4 * log2 0.4) = 0.971 bits. A pure node (10 negatives, 0 positives) gives Gini 0 and entropy 0. A perfectly mixed node (5/5) gives Gini 0.5 and entropy 1.0 bit - the maxima. So both measures run from 0 (pure) to a maximum at the even split, and they differ only in scale and curvature.",
              "A perfect split versus a useless one, in gain. Parent Gini 0.48. Split A produces children [0,0,0,0,0,0] and [1,1,1,1]: both pure, so the weighted child impurity is 0.6*0 + 0.4*0 = 0 and gain = 0.48. That is the maximum possible. Split B produces [0,0,0,1,1] and [0,0,0,1,1]: each child has Gini 0.48, so the weighted average is 0.48 and gain = 0. The tree learned nothing, and the gain formula says so numerically - which is exactly why you maximise gain rather than eyeballing the split.",
              "Why the average must be WEIGHTED, with a case that exposes it. A split producing one child of 1 sample (pure, Gini 0) and one child of 99 samples (Gini 0.49). Unweighted, the child impurity looks like (0 + 0.49)/2 = 0.245, a big apparent improvement over 0.48. Weighted, it is (1/100)*0 + (99/100)*0.49 = 0.485 - almost no improvement, which is the truth: peeling off one sample barely helps. Forgetting the weights makes the tree prefer splits that isolate single outliers, and that is exactly how it overfits.",
              "The high-cardinality bias, which is the trap to name unprompted. Give the tree a customer_id column. Splitting on it produces leaves containing one customer each, all perfectly pure, so the information gain is maximal and it wins every split. The tree has learned a lookup table that generalises to nobody. This is why C4.5 introduced gain RATIO (dividing the gain by the split's own entropy, which penalises many-way splits) and why you should never feed a tree a raw identifier. The same bias appears more subtly with continuous features that have many distinct values.",
              "Regression trees, which are the same algorithm with one substitution. Replace impurity with variance: pick the split that most reduces the weighted variance of the children, and each leaf predicts the MEAN of its members. A node holding [10, 12, 11, 13] has variance 1.25; splitting into [10,11] and [12,13] gives child variances of 0.25 each, so weighted 0.25 and a reduction of 1.0. Everything else - greedy search, stopping rules, pruning - is identical, which is worth saying because it shows the framework rather than two memorised algorithms.",
              "Why an unconstrained tree is useless, and what to do. Left alone, the tree splits until every leaf is pure - training accuracy exactly 100%, test accuracy poor, because the deepest splits are fitting noise in single samples. The constraints, in the order that matters: max_depth (the blunt one), min_samples_leaf (the most useful - a leaf built from 2 samples is a rumour), and min_impurity_decrease. Better still, do not tune a single tree at all: bag many of them into a random forest, where averaging cancels the individual trees' overfitting. That is the honest answer to 'how do you stop a tree overfitting?'.",
          ],
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
          examples=[
              "One iteration by hand, on six points in 1-D. Data [1, 2, 3, 10, 11, 12], k = 2, initial centroids at 2 and 3. ASSIGN: {1,2} go to centroid 2; {3,10,11,12} go to centroid 3. MOVE: centroids become 1.5 and 9.0. ASSIGN again: {1,2,3} to 1.5; {10,11,12} to 9.0. MOVE: 2.0 and 11.0. ASSIGN again: unchanged, so it has converged in three iterations. Note the bad initialisation still recovered here - it often does not, which is exactly why n_init exists.",
              "The elbow, read correctly. Inertia for k = 1..6 comes out 1000, 400, 180, 160, 150, 145. The drops are 600, 220, 20, 10, 5 - so the big gains stop after k = 3 and the curve bends there. Crucially, inertia keeps FALLING all the way to k = n, where it is exactly 0 (one cluster per point), so the minimum is useless as a criterion. You are looking for the bend, not the bottom. When the curve has no clear bend - which is common on real data - fall back to the silhouette score, which can honestly be maximised.",
              "Why k-means++ matters, with the failure it prevents. Random initialisation can drop two of three centroids inside the same true cluster; the algorithm converges happily to a local optimum that splits one real group in two and merges the other two. k-means++ picks each new seed with probability proportional to its squared distance from the nearest existing seed, so seeds spread out and this failure becomes rare. Combined with n_init=10 (run it ten times, keep the lowest inertia), the local-optimum problem largely disappears - and both are defaults in scikit-learn for exactly that reason.",
              "The scaling failure, in numbers. Customers with income (mean 50,000, sd 20,000) and age (mean 40, sd 10). Unscaled, income's variance is about 4,000,000 times age's, so Euclidean distance is essentially |income difference| and age contributes nothing measurable. Your 'customer segments' are income bands with age noise. After standardising both to mean 0 and sd 1, a 20-year age gap and a 20,000-euro income gap count equally - which is almost certainly what you meant. Always scale before k-means; it is not optional the way it is for trees.",
              "Where the assumptions break, and what to reach for instead. Two interleaving crescents (make_moons): k-means slices both in half, because it can only draw straight boundaries equidistant between centroids. DBSCAN recovers both crescents and labels the stragglers as noise, because it grows clusters by DENSITY rather than distance to a centre - and it needs no k. Similarly, clusters of very different sizes or densities defeat k-means (it splits the big one and merges the small ones), while Gaussian mixtures handle elliptical, differently-sized clusters via soft assignment.",
              "The honest caveat to state out loud: k-means ALWAYS returns k clusters, including on uniform random noise where no clusters exist. It has no notion of 'there is no structure here'. So before presenting segments to a stakeholder, check that the silhouette score is meaningfully above 0 (near 0 means the clusters barely separate), check stability by re-running on bootstrap samples, and sanity-check that the segments differ on features you did not cluster on. Clustering output is a hypothesis, not a finding.",
          ],
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
          examples=[
              "The MNIST number worth quoting. 784 pixel features reduce to about 150 components for 95% of the variance — so a kNN classifier runs roughly five times faster with almost no accuracy loss. The reason is that neighbouring pixels are heavily correlated: PCA is exploiting redundancy, not discarding information. That framing matters, because it tells you when PCA will help (correlated features) and when it will not (already-independent features, where the components are just a rotation and nothing can be dropped).",
              "The scaling trap, in numbers. Salary (mean 50,000, sd 20,000) and age (mean 40, sd 10). Salary's variance is about 4,000,000 times age's, so PC1 is essentially 'salary' and age contributes nothing measurable — you have rediscovered your largest-magnitude column and called it a discovery. Standardise first unless the units are genuinely comparable (all pixel intensities, all the same sensor). This is the single most common way PCA is misapplied.",
              "The failure case people do not expect: PCA is UNSUPERVISED. Imagine two classes separated along a low-variance direction, with a large irrelevant spread elsewhere — measurement noise on an unrelated sensor, say. PC1 captures the noise, you keep it and drop the direction that actually separates the classes, and the data becomes LESS separable after 'reducing' it. When you have labels and separation is the goal, LDA is the supervised alternative that maximises between-class over within-class variance.",
              "Choosing the component count honestly. Plot cumulative explained variance and take the smallest k reaching 90-95%, or look for the elbow in the scree plot. In scikit-learn you can pass the target directly: PCA(n_components=0.95). What you cannot do is pick k because it looks tidy — and note that explained variance says nothing about whether the retained directions are USEFUL for your task, only that they are wide.",
              "The leakage rule, which is the same one as everywhere else. Fit PCA on the TRAINING FOLD only, then transform validation and test. Fitting on the whole dataset lets test-set structure into the components, and the resulting optimism is small enough to be invisible and large enough to matter. Putting PCA inside a Pipeline makes this automatic, which is the practical answer rather than remembering to do it by hand.",
              "What you give up, stated plainly. Each component is a linear combination of EVERY original feature, so 'PC1' has no business meaning — you cannot tell a regulator that PC1 rose by 0.3. For a model that must be explained (credit, clinical risk), that is usually disqualifying, and feature SELECTION (keeping original columns) is the right tool instead. Also worth knowing: t-SNE and UMAP are for VISUALISATION only — they give no reusable transform, and distances between their clusters are not meaningful.",
          ],
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
          examples=[
              "XOR, the problem that defines the topic. Inputs (0,0) and (1,1) map to 0; (0,1) and (1,0) map to 1. Plot the four points: no straight line separates them, so logistic regression is stuck at 75% accuracy forever regardless of training time. One hidden layer of two ReLU neurons solves it exactly, because the first layer bends the space into a form where a line does work. This is not a toy detail - Minsky and Papert's 1969 proof that a perceptron cannot do XOR triggered the first AI winter, and the multi-layer fix is what ended it.",
              "The proof that the activation is the whole point, in algebra. Remove the ReLU so a1 = z1. Then the network computes (X W1 + b1) W2 + b2 = X (W1 W2) + (b1 W2 + b2) = X W' + b'. That is ONE linear layer. Stack a hundred of them and it collapses the same way, because a composition of linear maps is linear. So a deep network without non-linearity has exactly the representational power of logistic regression, no matter how many parameters it has. Being able to do that three-line expansion on a whiteboard is the strongest possible answer to 'why do we need activations?'.",
              "Why zero initialisation is fatal, and what to use instead. Set every weight to 0 (or to any single constant) and every neuron in a layer computes the same output, receives the same gradient, and updates identically - forever. The layer has the capacity of one neuron; this is the symmetry-breaking problem. Random initialisation breaks it, but the SCALE matters: He initialisation scales by sqrt(2/fan_in) for ReLU and Xavier/Glorot by sqrt(1/fan_in) for tanh, chosen so the variance of the signal is preserved layer to layer. Too small and the signal vanishes with depth; too large and it explodes.",
              "Depth versus width, and why depth won. The universal approximation theorem says ONE hidden layer with enough neurons can approximate any continuous function - so why go deep? Because 'enough' can be exponentially many. Depth composes: layer 1 finds edges, layer 2 combines edges into corners and textures, layer 3 into object parts, layer 4 into objects. Each layer reuses the layer below, so the same function needs exponentially fewer units than a single wide layer would. It also matches the actual structure of images, text and audio, which are hierarchical.",
              "The training loop, named so you can narrate it. FORWARD: compute predictions layer by layer, caching the activations. LOSS: score the error. BACKWARD: backpropagate, assigning each weight its share of the blame via the chain rule. STEP: nudge every weight against its gradient (Adam in practice, plain SGD in the textbook). Repeat per mini-batch; one pass over the whole dataset is an epoch. Four words - forward, loss, backward, step - and every deep-learning framework is that loop with engineering around it.",
              "When NOT to use one, which is the judgement half of the answer. On 500 rows of tabular data with mixed scales and a dozen columns, a gradient-boosted tree will beat a neural network with a fraction of the tuning, because tabular data is non-smooth, scale-heterogeneous and full of uninformative columns - all things trees handle natively and networks must learn. Neural networks earn their keep where representation learning pays: images, text, audio, very high-cardinality categoricals needing embeddings, and multi-modal problems. Saying this unprompted reads as judgement rather than enthusiasm.",
          ],
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
# Check: the new forward pass gives z = 0.4382 and a = 0.6078 - closer to the
# target of 1, and the loss falls from 0.9131 to 0.4979 in this single step.
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
              r"""1. THE GOAL - working out who is to blame.

A network makes a guess. The guess is wrong by some amount. Now you must decide, for every
single weight in the network - possibly billions of them - HOW MUCH THIS PARTICULAR WEIGHT
CONTRIBUTED TO THAT ERROR, and therefore which way and how far to move it.

That is the only job backpropagation does. It is not the learning rule - the sibling entry
"HOW GRADIENT DESCENT WORKS" owns the update step, w minus learning-rate times gradient. This
page owns where the gradient COMES FROM.

    forward:   inputs  ->  layer 1  ->  layer 2  ->  output  ->  loss
    backward:  loss    ->  who caused this?  <-  <-  <-  <-  <-

The name says it exactly: the error propagates BACKWARD through the layers, and each layer
hands its share of the blame to the layer beneath it.

And the mechanism is nothing more exotic than the CHAIN RULE from calculus:

    the loss changed because the output changed
    the output changed because the pre-activation changed
    the pre-activation changed because this weight changed

Multiply those three sensitivities together and you have how much the loss changes with that
weight. That is the whole idea. The cleverness is not in the calculus, it is in the ORDER:
computing backward lets every intermediate result be reused, which is why training a
billion-parameter network costs about the same as two forward passes rather than a billion of
them. Section 5 proves that.""",
              r"""2. THE INTUITION - blame flowing backward through a chain.

Take the smallest possible network - one neuron, two inputs - and follow the chain both ways.

    FORWARD:

        x1 = 2.0 --\
                    w1 = 0.5
                       \
                        (+) --> z = -0.4 --> [sigmoid] --> a = 0.4013 --> loss = 0.913
                       /                                     (target y = 1)
                    w2 = -0.5
        x2 = 3.0 --/
                          bias b = 0.1

    BACKWARD - the same path, in reverse, carrying blame:

        how much does the loss change if a changes?         dL/da = -2.4917
        how much does a change if z changes?                da/dz =  0.2403
        so how much does the loss change if z changes?      dL/dz = -0.5987
        how much does z change if w1 changes?               dz/dw1 = x1 = 2.0
        so how much does the loss change if w1 changes?     dL/dw1 = -1.1974

Each arrow backward is a MULTIPLICATION by one local sensitivity. Nothing more.

The quantity that matters most is the middle one, dL/dz - the blame attached to a neuron's
PRE-ACTIVATION. It has a name, DELTA, and once you have it for a layer, the weight gradients
are almost free:

    gradient for a weight  =  (the input that weight multiplied)  x  (this neuron's delta)

Which makes intuitive sense: a weight is more to blame when the input it was multiplying was
large. A weight sitting on an input of 0 could not have affected anything, and indeed its
gradient is 0.

    dL/dw1 = x1 x delta = 2.0 x (-0.5987) = -1.1974
    dL/dw2 = x2 x delta = 3.0 x (-0.5987) = -1.7961

Note w2's gradient is larger, purely because x2 was larger. Same delta, different share of the
blame.

For a deeper network, delta for one layer is computed from the delta of the layer ABOVE it -
blame flows down through the weights and then through the activation's slope. That recursion
is the whole algorithm, and section 8 writes it out.""",
              r"""3. EVERY TERM, defined the first time you meet it.

FORWARD PASS. Running inputs through the network to produce an output and a loss.

BACKWARD PASS. Working out every weight's gradient, starting from the loss and moving toward
the inputs.

PRE-ACTIVATION (z). The weighted sum plus bias, BEFORE the activation function.

ACTIVATION (a). The value after the activation function. This is what the next layer receives.

ACTIVATION FUNCTION. The non-linear bend applied to z - sigmoid, ReLU, tanh. Without one, a
stack of layers collapses into a single linear layer, so it is what makes depth meaningful.

SIGMOID. 1 / (1 + e-to-the-minus-z). Squashes anything into (0, 1). Its derivative is
a x (1 - a), which peaks at 0.25 - a number that turns out to matter enormously (section 5).

ReLU. max(0, z). Its derivative is exactly 1 for positive z and 0 otherwise. That exact 1 is
the single biggest reason deep networks became trainable.

LOSS. One number saying how wrong the output is.

GRADIENT. The derivative of the loss with respect to something. "How much would the loss
change if I nudged this?"

CHAIN RULE. If a depends on b and b depends on c, then how a changes with c is (how a changes
with b) times (how b changes with c). Backprop is this, applied repeatedly.

DELTA. The gradient of the loss with respect to a layer's PRE-ACTIVATION. The central quantity
- once you have it, weight gradients are one multiplication away.

PARTIAL DERIVATIVE, written dL/dw. How much L changes per unit change in w, holding everything
else fixed.

CACHED ACTIVATIONS. The intermediate values the forward pass stores because the backward pass
needs them. This is why TRAINING uses far more memory than INFERENCE, and section 10 quantifies
it.

VANISHING GRADIENT. Gradients shrinking toward zero as they travel back through many layers,
so early layers stop learning. Section 5 puts a number on it.

EXPLODING GRADIENT. The opposite - gradients growing until the weights become NaN. Fixed by
gradient clipping.

GRADIENT CHECKING. Verifying a hand-written gradient against a numerical estimate. How you
debug a custom layer.

AUTOMATIC DIFFERENTIATION (AUTOGRAD). What PyTorch and TensorFlow do: build a graph of
operations during the forward pass and apply these rules automatically. You will rarely write
backprop by hand - but you will be asked to explain it.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1 - THE ONE THAT KILLED DEEP LEARNING FOR TWENTY YEARS: VANISHING GRADIENTS.

Sigmoid's derivative is a(1 - a), which is at most 0.25 - and that maximum only occurs at
a = 0.5, right at the middle. Away from there it is far smaller.

Now stack ten sigmoid layers. The gradient reaching layer 1 has been multiplied by that
derivative once per layer:

    0.25 to the power of 10  =  0.00000095  -  about one in a million

    even in the BEST case, at every layer's most favourable point

So the first layer receives a gradient a million times weaker than the last. It effectively
does not learn at all, while the top layers train normally. The network appears to be training
- the loss goes down - and its early layers, which are supposed to learn the basic features
everything else builds on, are frozen.

THE FIX, and why it worked: ReLU's derivative is EXACTLY 1 for positive inputs. Ten layers
multiply by 1 ten times, which is 1. Nothing shrinks. That single change - along with residual
connections, which give gradients a path that skips layers entirely - is the main reason
networks went from about 5 layers to hundreds.

TRAP 2: pairing sigmoid with squared error. The gradient dL/dz then carries an extra factor of
the sigmoid's slope, which collapses toward zero exactly when the model is most confidently
wrong. With cross-entropy that factor CANCELS and dL/dz becomes simply (a - y). Section 9 shows
the cancellation happening in the trace. The logistic regression sibling quantifies it - about
203 times weaker at z = -6.

TRAP 3: forgetting that the forward pass must CACHE its activations. The weight gradient for a
layer is "that layer's INPUT times its delta" - so you need the input, which is the previous
layer's activation, computed during the forward pass. That is why training a model needs far
more memory than running it, and why batch size is limited by memory rather than by principle.

TRAP 4: initialising all weights to zero. Every neuron in a layer then computes the same thing,
receives the same gradient, and updates identically - forever. They stay identical, so the layer
has the effective capacity of one neuron. Small random values break the symmetry. (Note this is
the opposite of linear and logistic regression, where zero initialisation is perfectly safe
because there is no symmetry to break.)

TRAP 5: thinking backprop is the learning algorithm. It computes gradients. Gradient descent
uses them. Adam, momentum and RMSProp are all variations on the USE, not the computation - so
"we use Adam instead of backprop" is a confusion worth avoiding out loud.

TRAP 6: not gradient-checking a hand-written layer. The numerical estimate
(loss(w + eps) - loss(w - eps)) / (2 x eps) should match your analytic gradient to about seven
digits. If it does not, your derivative is wrong, and a wrong gradient does not crash - it
trains slowly to a worse answer, which is far harder to notice.""",
              r"""5. THE NAIVE METHOD FIRST, THEN THE REAL ONE - AND WHY BACKWARD.

THE NAIVE VERSION - NUMERICAL DIFFERENTIATION. Nudge each weight and see what happens.

    for each weight:
        add a tiny amount to it
        run the whole network forward and record the loss
        subtract the tiny amount instead, run forward again
        the gradient is (loss_up - loss_down) / (2 x tiny amount)

This is completely correct, and it is what gradient checking uses. It is also unusable for
training, and the arithmetic shows why:

    a network with 1,000,000 weights
    each gradient needs 2 forward passes
    -> 2,000,000 forward passes to compute ONE gradient step

    if a forward pass takes 10 milliseconds, that is 20,000 seconds - about 5.5 HOURS
    for a single update. And you need thousands of updates.

BACKPROPAGATION COMPUTES ALL 1,000,000 GRADIENTS IN ROUGHLY ONE FORWARD PASS'S WORTH OF EXTRA
WORK - typically about twice the cost of a forward pass. Call it 30 milliseconds instead of
20,000 seconds, a speed-up of around 600,000 times.

WHY GOING BACKWARD IS WHAT BUYS THAT - the argument, because this is the actual content of the
algorithm:

Consider a chain: the loss depends on layer 3, which depends on layer 2, which depends on layer
1. To get the gradient for a weight in layer 1, you need the product of every sensitivity along
the path from that weight up to the loss.

    GOING FORWARD, you would start at each weight and multiply your way up to the loss. Every
    weight's path passes through layers 2 and 3, so you recompute those same upper sensitivities
    once per weight. A million weights means a million recomputations of the same numbers.

    GOING BACKWARD, you start at the loss and compute the sensitivity of the loss to layer 3
    ONCE. Then to layer 2 once. Then to layer 1 once. Every weight in layer 1 reuses the same
    already-computed chain, and only needs its own final multiplication by its input.

THE SHARED PART IS COMPUTED ONCE INSTEAD OF ONCE PER WEIGHT. That is the whole efficiency
argument, and it is why the algorithm has "back" in its name - the direction is not
incidental, it is the entire point.

THE RECURSION THAT MAKES IT WORK. Define delta for a layer as the gradient of the loss with
respect to that layer's pre-activation. Then:

    delta for the last layer  =  comes directly from the loss function
    delta for layer L         =  (the layer above's delta, sent back through the weights)
                                 times (this layer's activation slope)

    and once you have delta:      weight gradient  =  this layer's INPUT  x  delta
                                  bias gradient    =  delta

Two multiplications per layer, reusing everything from the layer above.

THE UPGRADE THAT MADE IT PRACTICAL AT DEPTH: choosing activations whose slope is 1 rather than
at most 0.25 (ReLU), and adding residual connections so gradients have a direct path that skips
layers entirely. Both attack the multiplication chain from trap 1.""",
              r"""6. HOW TO DO IT - the steps, in plain English.

The one sentence that holds the whole idea: RUN FORWARD KEEPING EVERY INTERMEDIATE VALUE, THEN
WALK BACKWARD MULTIPLYING BY ONE LOCAL SENSITIVITY PER STEP, SO THAT EACH LAYER'S BLAME IS
COMPUTED ONCE AND REUSED BY EVERY WEIGHT BENEATH IT.

THE LOOP HERE IS THE WALK BACKWARD THROUGH THE LAYERS, and it is worth being precise:

  - It is not recursion in the call-stack sense, though it is often written that way. It is a
    fixed walk from the last layer to the first.
  - Each step consumes the delta from the layer ABOVE and produces the delta for the layer
    BELOW. Nothing else crosses between steps.
  - WHAT MAKES IT STOP: reaching the input layer. There is nothing below it to blame, and the
    inputs are not parameters. The trip count is exactly the number of layers - known in
    advance, so termination is guaranteed.
  - WHAT IT NEEDS FROM THE FORWARD PASS: every layer's input. If those were not cached, the
    weight gradients cannot be formed and you would have to recompute the forward pass, which
    is exactly the trade some memory-saving techniques make deliberately.

THE STEPS:

  1. FORWARD PASS. For each layer in order: compute the weighted sum plus bias, apply the
     activation, pass it on. CACHE each layer's input and pre-activation as you go - the
     backward pass needs them.

  2. COMPUTE THE LOSS from the final output and the target.

  3. START THE BACKWARD PASS at the output: work out how much the loss changes with the final
     pre-activation. For the standard pairings - sigmoid with binary cross-entropy, softmax with
     cross-entropy - this collapses to simply (prediction minus target), which is why those
     pairings are used everywhere.

  4. FOR EACH LAYER, FROM LAST TO FIRST:

     a. FORM THE WEIGHT GRADIENTS: this layer's cached INPUT times this layer's delta. That is
        the whole formula, and it says a weight is blamed in proportion to the input it was
        multiplying.

     b. FORM THE BIAS GRADIENT: just the delta, since the bias multiplies a constant 1.

     c. SEND THE BLAME DOWN: multiply the delta by this layer's weights, which distributes the
        blame across the neurons below in proportion to how strongly each was connected.

     d. PASS IT THROUGH THE ACTIVATION: multiply by the slope of the layer below's activation
        at its cached pre-activation. This is where vanishing gradients happen - if that slope
        is small, everything below shrinks.

     e. That product is the layer below's delta. Continue.

  5. HAND EVERY GRADIENT TO THE OPTIMISER, which does the actual updating - the gradient
     descent sibling.

  6. IF YOU WROTE THE LAYER BY HAND, GRADIENT-CHECK IT before trusting it. A wrong gradient does
     not crash; it silently trains to a worse answer.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

A parcel arrives at a customer three days late. A manager wants to know who needs to change
what.

The naive way: go to every single person in the chain - all thousand of them - and for each,
ask "if you had worked slightly faster, how much earlier would the parcel have arrived?" To
answer even one of those, you would have to re-run the entire delivery in your head from that
person all the way to the customer. A thousand people, a thousand full re-runs. It would take
longer than the delivery did.

The clever way runs backward, once.

Start at the customer. Three days late. Ask the final courier: how much of this was yours? She
says one day was hers - and, crucially, she can also say how much of the remaining two days
came from each of the three depots that fed her, in proportion to how much she depended on
each.

So each depot receives its share of the blame. Now each depot does the same thing for its own
suppliers, dividing its share among them.

Each person in the chain is asked exactly ONCE. And here is the saving: when a depot works out
its own share, it does not need to re-run the rest of the journey to the customer, because the
courier already worked that part out and handed the number down. The expensive shared part of
the calculation was done once, at the top, and everybody below inherits it.

Two details that come straight from the story.

To answer "how much was yours", each person has to remember what they were handed and when.
If nobody kept records of the delivery, you would have to re-run it just to ask. That is why
training keeps every intermediate value in memory, and why it needs so much more memory than
simply making a delivery.

And there is a way this goes wrong. Suppose every person in the chain, when passing blame
down, keeps three-quarters of it and passes only a quarter. After ten links, the person at the
very start receives about a millionth of the original blame - effectively nothing. They never
learn they were part of the problem, and they keep doing exactly what they were doing. Fixing
that meant finding links that pass blame down undiminished.""",
              r"""8. THE CODE, LINE BY LINE, in the real variable names.

    x = np.array([2.0, 3.0]); w = np.array([0.5, -0.5]); b = 0.1; y = 1.0

Two inputs, two weights, one bias, and a target of 1. Small enough that every number below can
be checked by hand, which is the point of the example.

    # FORWARD
    z = w @ x + b                      # 0.5*2 + (-0.5)*3 + 0.1 = -0.4

The PRE-ACTIVATION: the dot product of weights and inputs, plus the bias. z can be any number
- it is not yet a probability. This value must be REMEMBERED, because the backward pass needs
it.

    a = 1 / (1 + np.exp(-z))           # sigmoid(-0.4) = 0.4013

The ACTIVATION: squash z into (0, 1). The neuron's output. Also cached.

    loss = -(y * np.log(a) + (1 - y) * np.log(1 - a))     # 0.9130

Binary cross-entropy. With y = 1 the second term vanishes, so the loss is just -log(a). The
model said 0.4013 for something that was 1, and is charged 0.913 for it.

    # BACKWARD - three chain-rule links
    dL_da = -(y / a) + (1 - y) / (1 - a)      # dLoss/da   = -2.4917

LINK ONE: how much does the loss change if the OUTPUT changes? Differentiating -log(a) gives
-1/a, which at a = 0.4013 is -2.4917. Negative, meaning increasing a would DECREASE the loss -
correct, since the target is 1 and we are below it.

    da_dz = a * (1 - a)                       # dsigmoid   =  0.2403

LINK TWO: how much does the output change if the pre-activation changes? The sigmoid's
derivative has the tidy form a(1-a) - one reason sigmoid was popular. Note the value: 0.2403,
already below the theoretical maximum of 0.25, and this is a SINGLE layer. Trap 1 is this
number raised to the power of the depth.

    dL_dz = dL_da * da_dz                     # = a - y    = -0.5987  <- the shortcut

LINK THREE, and the most important line here. Multiply the two sensitivities - the chain rule -
and you get the DELTA: how much the loss changes with the pre-activation.

But look at the comment: the answer equals (a - y). That is not a coincidence, it is an exact
cancellation. The -1/a from the logarithm cancels against the a(1-a) from the sigmoid, leaving
(a - y). Verified in section 9.

THAT CANCELLATION IS WHY SIGMOID IS PAIRED WITH CROSS-ENTROPY. With squared error the a(1-a)
factor survives, and it collapses toward zero exactly when the model is most confidently wrong.
The same cancellation happens for softmax with cross-entropy, which is why that pairing is
universal.

    dL_dw = dL_dz * x                         # [-1.1974, -1.7961]

THE WEIGHT GRADIENTS: delta times the INPUT. One line, and it carries the whole idea of blame
assignment - w2's gradient is larger only because x2 (3.0) was larger than x1 (2.0). A weight
that multiplied a bigger input had more influence, so it gets more blame.

    dL_db = dL_dz                             # -0.5987

The bias multiplies a constant 1, so its gradient IS the delta. No input factor.

    w_new = w - 0.1 * dL_dw                   # [0.6197, -0.3204]
    b_new = b - 0.1 * dL_db                   # 0.1599

The update - and note this is the gradient descent sibling's rule, not backprop's. Backprop's
job finished when the gradients were computed.

    def backward_layer(dz_next, W_next, z, activation_grad, a_prev):
        da   = dz_next @ W_next.T              # blame flows back through the weights

THE RECURSION, one step. dz_next is the delta of the layer ABOVE. Multiplying by that layer's
weights transposed distributes its blame down to this layer's outputs, in proportion to how
strongly each connection carried influence upward.

        dz   = da * activation_grad(z)         # through the activation

Then through this layer's activation slope, evaluated at the CACHED pre-activation z. This
single multiplication is where vanishing gradients occur - if activation_grad returns 0.25
here, everything below is quartered.

        dW   = a_prev.T @ dz                   # INPUT to this layer times its delta

The same rule as the single neuron: input times delta. a_prev is the cached activation of the
layer below, which is this layer's input - the reason the forward pass had to store it.

        db   = dz.sum(axis=0)

Summed over the batch, because every example in the batch contributes to the same bias.

    relu_grad = lambda z: (z > 0).astype(float)

ReLU's derivative: exactly 1 where z is positive, 0 elsewhere. That EXACT 1 is the fix for trap
1 - ten layers multiply by 1 ten times and nothing shrinks.

    def softmax_ce_grad(logits, y_onehot):
        e = np.exp(logits - logits.max(axis=1, keepdims=True))   # stable softmax

Subtracting the row maximum before exponentiating prevents overflow and provably does not change
the result - the common factor cancels top and bottom. The self-attention sibling proves it.

        return (probs - y_onehot) / len(logits)      # that is the WHOLE gradient

The multi-class version of the same cancellation: predictions minus one-hot targets, averaged
over the batch. No activation-derivative factor anywhere. This is why softmax and cross-entropy
are always used together.

    0.25 ** 10

Vanishing gradients as a single expression: 9.5e-7. Section 9.""",
              r"""9. TRACED WITH REAL NUMBERS.

THE COMPLETE SINGLE-NEURON UPDATE.

    SETUP:  x = [2.0, 3.0],  w = [0.5, -0.5],  b = 0.1,  target y = 1
            sigmoid activation, binary cross-entropy loss, learning rate 0.1

    FORWARD:

        z = 0.5 x 2.0 + (-0.5) x 3.0 + 0.1
          = 1.0 - 1.5 + 0.1
          = -0.4

        a = 1 / (1 + e-to-the-0.4) = 1 / (1 + 1.49182) = 1 / 2.49182 = 0.401312

        loss = -[1 x ln(0.401312) + 0 x ln(0.598688)]
             = -ln(0.401312)
             = 0.913081

    BACKWARD:

        dL/da = -(y/a) = -(1 / 0.401312) = -2.491825

        da/dz = a(1 - a) = 0.401312 x 0.598688 = 0.240262

        dL/dz = -2.491825 x 0.240262 = -0.598690

    THE CANCELLATION, CHECKED:

        a - y = 0.401312 - 1 = -0.598688

        The chain-rule product gave -0.598690; the shortcut gives -0.598688. Identical to five
        decimal places, the difference being rounding in the intermediate values. The -1/a and
        the a(1-a) cancelled exactly, as they must.

    WEIGHT GRADIENTS:

        dL/dw1 = dL/dz x x1 = -0.598688 x 2.0 = -1.197376
        dL/dw2 = dL/dz x x2 = -0.598688 x 3.0 = -1.796064
        dL/db  = dL/dz                        = -0.598688

        w2's gradient is exactly 1.5 times w1's, because x2 is 1.5 times x1. Same delta,
        blame split by input size.

    UPDATE, learning rate 0.1:

        w1_new = 0.5  - 0.1 x (-1.197376) = 0.5  + 0.119738 = 0.619738
        w2_new = -0.5 - 0.1 x (-1.796064) = -0.5 + 0.179606 = -0.320394
        b_new  = 0.1  - 0.1 x (-0.598688) = 0.1  + 0.059869 = 0.159869

    DID IT HELP? Run the forward pass again with the new parameters:

        z_new = 0.619738 x 2.0 + (-0.320394) x 3.0 + 0.159869
              = 1.239476 - 0.961182 + 0.159869
              = 0.438163

        a_new = 1 / (1 + e-to-the-minus-0.438163) = 1 / (1 + 0.645244) = 0.607813

        loss_new = -ln(0.607813) = 0.497948

    The output moved from 0.4013 to 0.6078 - toward the target of 1 - and the loss fell from
    0.9131 to 0.4979, roughly halving in a single step. (Note the pre-activation crossed zero,
    from -0.4 to +0.438, so this one step flipped the prediction from "class 0" to "class 1".)

VANISHING GRADIENTS, QUANTIFIED - why depth was impossible for so long:

    sigmoid's derivative a(1-a), at its very best, is 0.25 (at a = 0.5). Through a stack:

        1 layer:    0.25                       gradient reduced 4x
        2 layers:   0.0625                     16x
        5 layers:   0.000977                   about 1,000x
        10 layers:  0.00000095                 about 1,000,000x
        20 layers:  0.00000000000091           about a trillion x

    And that is the BEST case. In the trace above the derivative was 0.2403, already below the
    maximum, and a neuron sitting at a = 0.9 has a derivative of 0.09 - which through ten layers
    gives 3.5e-11.

    THE FIX, in the same units:

        ReLU's derivative is exactly 1 for positive inputs.

        1 layer:    1
        10 layers:  1
        100 layers: 1

    NOTHING SHRINKS. That is the entire reason the field moved from sigmoid to ReLU, and it is
    a one-line comparison worth being able to produce.

THE EFFICIENCY ARGUMENT, in the same style:

    a network with 1,000,000 weights, forward pass 10 milliseconds

        NUMERICAL:  2 forward passes per weight
                    = 2,000,000 passes x 10 ms = 20,000 seconds = about 5.5 HOURS per update

        BACKPROP:   about 2 forward passes TOTAL
                    = roughly 30 ms per update

        Ratio: about 600,000 times faster - and the gap widens with every weight you add,
        because numerical differentiation scales with the parameter count while backprop does
        not.

GRADIENT CHECKING, the numbers to expect:

    numerical estimate = (loss(w + 1e-5) - loss(w - 1e-5)) / (2 x 1e-5)

    Compare with the analytic gradient using RELATIVE error:

        |analytic - numerical| / (|analytic| + |numerical|)

        below 1e-7   ->  correct
        around 1e-5  ->  suspicious, possibly a subtle bug
        above 1e-3   ->  your derivative is wrong

    Use it on a tiny network only - it costs two forward passes per weight, which is exactly
    what makes it unusable for training and perfectly fine for debugging.""",
              r"""10. THE COSTS IN PLAIN WORDS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT IT COSTS:

  - TIME: the backward pass is roughly twice the forward pass, so a training step is about
    three times an inference step. Crucially this is INDEPENDENT of the parameter count in the
    sense that matters - it does not scale with the number of weights the way numerical
    differentiation does.
  - MEMORY: this is the real cost, and it follows directly from the algorithm. The weight
    gradient for a layer is "that layer's INPUT times its delta", so every layer's input must
    be kept alive from the forward pass until the backward pass reaches it. Training therefore
    holds activations for the entire depth, for every example in the batch.

    THIS IS WHY TRAINING NEEDS FAR MORE MEMORY THAN INFERENCE, and why batch size is capped by
    memory rather than by any principle. Inference can discard each layer's output as soon as
    the next layer has consumed it; training cannot.

  - GRADIENT CHECKPOINTING is the standard trade: cache only some layers' activations and
    recompute the rest during the backward pass. Roughly 30% more time for a large memory
    saving - and knowing this trade exists is a good signal in an interview.

FOLLOW-UPS WORTH HAVING READY:

  - "Why is it computed backward rather than forward?" Because the sensitivities near the output
    are shared by every weight below them. Backward computes each shared piece once; forward
    would recompute it once per weight. Section 5 has the 600,000x arithmetic.
  - "What causes vanishing gradients and how do you fix them?" Multiplying by activation slopes
    at every layer. Sigmoid's peaks at 0.25, so ten layers give 0.25^10, about one in a million.
    Fix with ReLU (slope exactly 1), residual connections (a path that skips layers entirely),
    and normalisation layers.
  - "Why does training use more memory than inference?" Cached activations, needed because each
    weight gradient is input times delta.
  - "Why softmax with cross-entropy?" The gradient collapses to (predictions minus one-hot),
    with no activation-derivative factor to vanish. The same cancellation as sigmoid with binary
    cross-entropy, demonstrated in section 9.
  - "How would you debug a custom layer?" Gradient checking against the numerical estimate, with
    relative error below 1e-7.
  - "Is backprop how the brain learns?" No, and it is worth saying so plainly - it requires
    symmetric weights for the backward path and a global error signal, neither of which biology
    appears to have. It is an efficient algorithm, not a model of neuroscience.

WHERE THIS SITS: backprop COMPUTES the gradients; "HOW GRADIENT DESCENT WORKS" owns what is done
with them, including learning rates and Adam. The logistic regression sibling owns why the
sigmoid/cross-entropy pairing matters, quantified.

THE #1 MISTAKE: confusing backpropagation with gradient descent, and saying things like "we use
Adam rather than backprop". Backprop produces the gradients; Adam consumes them. They are
different stages, and every optimiser in existence still needs backprop underneath.

RUNNER-UP: initialising all weights to zero, which makes every neuron in a layer identical
forever, since identical weights receive identical gradients and update identically.

TAKEAWAY: backpropagation is the chain rule walked backward so that each layer's blame is
computed once and reused by every weight beneath it - which turns a calculation that would take
hours per step into one costing about two forward passes.""",
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
          examples=[
              "Saturation, in numbers you can quote. sigmoid'(z) evaluated at z = -10, -1, 0, 1, 10 gives 0.000045, 0.197, 0.25, 0.197, 0.000045. So a neuron whose pre-activation drifts beyond about |4| receives essentially no gradient and stops learning - it is 'saturated'. ReLU's derivative at the same points is 0, 0, 0, 1, 1: exactly 1 wherever the input is positive, with no decay at all. That single comparison is why hidden layers moved from sigmoid to ReLU and why networks went from about five layers to hundreds.",
              "Dying ReLU, and how to detect it. One large gradient step pushes a neuron's pre-activation permanently negative. Now relu(-3) = 0 and its derivative is 0, so the neuron outputs nothing and receives no gradient - it is dead forever, and a too-high learning rate can kill a whole layer at once. The symptom is a loss that plateaus at a bad value and never moves again. Diagnose it by logging the fraction of zero activations per layer: above roughly 50% is suspicious, near 100% means the layer is gone. Fixes: lower the learning rate, or use Leaky ReLU, whose -0.03 output at z = -3 carries a gradient of 0.01 - small, but enough to revive.",
              "The multi-label trap, which is the most common real bug here. Tagging a photo that is genuinely both 'beach' and 'sunset': softmax forces the outputs to sum to 1, so the two true tags must SHARE the probability budget and each scores about 0.5 - and the more tags an image truly has, the lower every one of them scores. Independent per-label sigmoids let both be 0.95 at once, because each asks its own yes/no question. Rule: softmax when exactly one class is correct, sigmoid-per-label when any number can be.",
              "Choosing the OUTPUT activation, which is a different question from the hidden ones. Regression: NONE - a raw linear output, because a sigmoid would silently cap your predictions at 1 and a ReLU would make negatives impossible. Binary classification: sigmoid with binary cross-entropy. Multi-class, one correct: softmax with categorical cross-entropy. Multi-label: sigmoid per label. Predicting a strictly positive quantity like a duration: either no activation on log(y), or softplus - and say which, because 'ReLU on the output' quietly makes the model unable to express any error below zero.",
              "Why softmax needs the max subtracted. exp(1000) overflows to inf in float32, and inf/inf is nan - so a large logit destroys the entire batch. Subtracting the row maximum first leaves the result mathematically identical (the constant cancels in the ratio) while keeping every exponent at or below zero. Every framework does this internally, which is also why you should pass LOGITS to a library's cross-entropy function rather than pre-applying softmax yourself: the fused version is both more stable and cheaper.",
              "Why transformers use GELU rather than ReLU. GELU multiplies x by the probability that a standard normal draw falls below it, giving a smooth curve that is slightly negative just below zero instead of a hard corner at the origin. The practical effect is a non-zero gradient in that region and a smoother loss surface, which empirically trains very large models a little better. The gain is small and consistent rather than dramatic - which is the honest thing to say. SiLU/Swish (x times sigmoid(x)) is the same idea and is used in Llama-family models.",
          ],
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
          examples=[
              "MSE versus MAE, decided by one number. Data [10, 12, 11, 13, 200] with one outlier. The constant prediction minimising MSE is the MEAN, 49.2 — wrong for four of the five points. The constant minimising MAE is the MEDIAN, 12 — right for four and ignoring the outlier. So the choice of loss IS a decision about how much outliers should count, and it changes the model's behaviour on the ordinary cases, not just on the extremes.",
              "Why confidently wrong is punished so hard by cross-entropy. Binary cross-entropy for a true label of 1: predicting 0.99 costs 0.01, predicting 0.50 costs 0.69, predicting 0.01 costs 4.61. Being confidently wrong costs about 460 times being confidently right — which is exactly the incentive you want, because it forces the model to express uncertainty rather than guess boldly. A loss that punished all errors equally would produce a model happy to be 99% sure and wrong.",
              "The pairing rule, stated as gradients. Sigmoid + binary cross-entropy gives dLoss/dz = (p - y) — clean, and largest precisely when the model is most wrong. Sigmoid + MSE gives (p - y) * p * (1-p), and that extra factor VANISHES when p is near 0 or 1. So with MSE a confidently wrong prediction (y=1, p=0.01) produces a gradient of -0.0098 instead of -0.99: the model learns most slowly exactly when it most needs to move. That is the mechanical reason for the pairing, not a convention.",
              "Focal loss, and the arithmetic that shows why it exists. In object detection 99.9% of candidate regions are easy negatives. With plain cross-entropy their tiny individual losses sum to swamp the few hard positives. Focal loss multiplies by (1-p_t)^gamma: an easy negative predicted at 0.99 contributes (0.01)^2 = 0.0001 of its usual weight — a 10,000x reduction — while a hard example near 0.5 is barely touched. That reweighting is what made one-stage detectors trainable.",
              "Encoding business cost directly in the loss. If missing a fraud costs ten times a false alarm, weight the positive class by 10 in the cross-entropy rather than training on a symmetric loss and patching it at the threshold afterwards. Both approaches can work, but weighting the loss makes the model optimise for the real objective during training, whereas threshold tuning only relabels the outputs of a model that was optimising something else.",
              "Why you cannot train on accuracy or F1 directly. Both are step functions of the predictions — change a probability from 0.51 to 0.52 and nothing moves until it crosses the threshold, so the gradient is zero almost everywhere. You optimise a differentiable SURROGATE (cross-entropy) and then tune the threshold to maximise F1 on a validation set. That two-stage structure — smooth loss for training, business metric for the decision — is the general pattern, and it is why the loss and the metric are almost never the same thing.",
          ],
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
          examples=[
              "Target leakage, the textbook case. Predicting hospital readmission with a feature 'discharge medication changed'. AUC 0.97, everyone celebrates. The problem: that field is only populated AFTER a readmission, during the second admission. At prediction time - the moment of first discharge - it is always empty, so the model has nothing to work with and collapses to near-random in production. The detector is simple: for every feature, ask WHEN the value is written relative to the label, not just what it means.",
              "Train-test contamination, which is the one people commit without noticing. `X_scaled = StandardScaler().fit_transform(X)` followed by train_test_split. The scaler computed its mean and standard deviation from the FULL dataset, so the test rows influenced the transform applied to the training rows. The leak is small - usually a fraction of a point of score - which is what makes it insidious: it silently inflates every number you report. The fix costs nothing: put every transform in a Pipeline so each cross-validation fold fits its own scaler on its own training rows.",
              "Temporal leakage, with the arithmetic that shows the damage. Daily sales for 2024, split randomly 80/20. December rows land in training and November rows in test, so the model predicts November having already seen December - including the Christmas ramp. Backtest R-squared 0.94, live performance barely better than a seasonal average. The rule is absolute: if the data has a time dimension and you will predict the future, the split must be by time, with train strictly earlier than test. Use TimeSeriesSplit and assert train.max() < test.min().",
              "Group leakage. A medical dataset with 10,000 scans from 2,000 patients, five scans each. Random splitting puts scans of the SAME patient in both train and test, so the model can memorise 'this is patient 447, who has the condition' rather than learning what the condition looks like. Accuracy 0.95 in validation, 0.71 on a new hospital's patients. GroupKFold with patient id as the group is the fix, and the same applies to users, devices, sessions and augmented copies of one source image.",
              "Leakage through the test set itself, which happens slowly. You tune hyperparameters against the test set, look at the score, adjust, look again - forty times. No single look is cheating, but after forty you have used the test set as a training signal, and your final reported number is optimistically biased by however much you searched. The discipline: tune on validation or with cross-validation, and touch the test set exactly ONCE, at the end. If you need an unbiased estimate of a tuned model, use nested cross-validation.",
              "The smell test to run before you celebrate. Any suspiciously high score should trigger three checks. (1) Sort feature importances - if one feature carries more than half the signal, investigate its provenance. (2) Retrain without that feature; if the score falls off a cliff, you have found the leak rather than a great feature. (3) Ask 'at the exact moment I need the prediction in production, do I have this value?' for the top ten features. That third question catches more leakage than any statistical test, and it is what the interviewer wants to hear you say out loud.",
          ],
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
              r"""1. THE GOAL - this entry is the MAP, not the territory.

Every model needs a number that says how well it is doing. There are dozens of candidate
numbers, they disagree with each other, and choosing the wrong one is how teams ship
models that score beautifully and fail in production.

The rule underneath all of it, and it is one sentence:

    PICK THE METRIC THAT MATCHES THE DECISION AND THE COST OF EACH ERROR - THEN JUSTIFY
    IT.

Not "which metric is best" - there is no such thing. A metric is a claim about what you
care about. Accuracy claims that all errors cost the same. RMSE claims that one error of
60 is worse than sixty errors of 1. NDCG claims that position 1 matters more than
position 5. Each of those claims is right for some problems and wrong for others.

WHAT THIS ENTRY OWNS, AND WHAT ITS SIBLINGS OWN - worth stating, because there are three
overlapping entries and reading all of them should not feel repetitive:

    THIS ENTRY  - the complete map across ALL task types, the routing rules, and
                  REGRESSION and RANKING metrics in depth. Plus the code that computes
                  them.
    PRECISION vs RECALL (sibling) - the confusion matrix and the choice between those two
                  in depth, plus the 95%-accuracy trap.
    ROC, AUC & CHOOSING A THRESHOLD (sibling) - the threshold sweep, ranking quality
                  versus operating point, and ROC versus PR under imbalance.

So classification is summarised here and developed there. Regression and ranking are
developed here, because nothing else covers them.""",
              r"""2. THE INTUITION - a routing table, keyed on what kind of answer the model gives.

Start from the SHAPE of the prediction, because that alone eliminates most of the menu:

    WHAT THE MODEL OUTPUTS            WHICH FAMILY OF METRICS
    ------------------------------    -------------------------------------------------
    a CLASS (spam / not spam)      -> accuracy, precision, recall, F1
    a PROBABILITY (0.83)           -> ROC-AUC, PR-AUC, log loss, Brier score
    a NUMBER (42.7 minutes)        -> RMSE, MAE, MAPE, R-squared
    an ORDERED LIST (10 results)   -> precision@k, recall@k, MAP, NDCG, MRR
    GROUPS with no labels          -> silhouette, Davies-Bouldin

Then, within a family, the question is what the errors cost:

    CLASSIFICATION
        classes balanced, errors equally bad          -> accuracy is fine
        false alarms expensive                        -> precision
        misses expensive                              -> recall
        want one number, errors roughly equal         -> F1
        want one number, errors NOT equal             -> F-beta
        judging the RANKING, classes balanced         -> ROC-AUC
        judging the RANKING, positives rare           -> PR-AUC
        the PROBABILITIES themselves get used         -> log loss

    REGRESSION
        big errors disproportionately bad             -> RMSE
        "the typical error is X minutes"              -> MAE
        errors matter in PERCENTAGE terms             -> MAPE (never near zero)
        "how much variance is explained"              -> R-squared

    RANKING
        only the first page matters                   -> precision@k
        position within the page matters              -> NDCG
        one right answer, how far down is it          -> MRR

The single most useful habit on this page: BEFORE choosing, write down what a wrong
answer costs in each direction, in real units. Once that is written, the metric usually
picks itself, and the choice becomes defensible rather than conventional.""",
              r"""3. EVERY TERM, defined the first time you meet it.

CONFUSION MATRIX. The 2x2 table of TP, FP, FN, TN. Everything in classification is
arithmetic on it. (Developed in the Precision vs Recall sibling.)

ACCURACY = (TP+TN)/total. Fraction correct. Meaningless on imbalanced data because TN
dominates.

PRECISION = TP/(TP+FP). Of what you flagged, how much was real.

RECALL = TP/(TP+FN). Of what was real, how much you caught. Also called sensitivity and
true positive rate.

SPECIFICITY = TN/(TN+FP). Of the true negatives, how many you correctly ignored.

F1 = harmonic mean of precision and recall. Low if either is low.

F-BETA. F1 generalised so recall counts beta times as much as precision. beta = 2 weights
recall more; beta = 0.5 weights precision more.

ROC-AUC. Area under the true-positive-rate versus false-positive-rate curve.
Threshold-independent; measures RANKING. Optimistic under heavy imbalance.

PR-AUC. Area under the precision-recall curve. The honest choice when positives are rare.
Its random baseline is the BASE RATE, not 0.5.

LOG LOSS (cross-entropy). Measures the quality of the PROBABILITIES themselves, not just
the class. Punishes confident wrongness enormously - predicting 0.99 for something that
was false costs far more than predicting 0.6. Use it when the probability feeds a
decision, such as expected-value calculations in bidding or pricing.

BRIER SCORE. Mean squared error of the probabilities. Same purpose as log loss, gentler
on confident mistakes.

CALIBRATION. Whether a predicted 0.7 really happens about 70% of the time. A model can
rank perfectly (great AUC) and be badly calibrated.

RMSE (Root Mean Squared Error). Square the errors, average, square-root. Same units as
the target. Squaring means one large error outweighs many small ones.

MAE (Mean Absolute Error). Average of absolute errors. Robust to outliers, and the one
that supports the sentence a stakeholder actually understands: "we are typically off by
14 minutes".

MAPE (Mean Absolute Percentage Error). Average of |error / actual|. Scale-free, and it
explodes when the true value is near zero - dividing by 0.001 produces a percentage in the
thousands.

R-SQUARED. Share of the target's variance the model explains. 1.0 perfect, 0 no better
than predicting the mean, and it can be negative. It NEVER DECREASES when you add a
feature, even a useless one - which is why adjusted R-squared exists.

PRECISION@k. Precision computed on only the top k results, because users see one page.

NDCG (Normalised Discounted Cumulative Gain). Ranking metric that rewards putting the
most relevant items HIGHEST, with a logarithmic discount by position, normalised against
the perfect ordering so it lands between 0 and 1.

MRR (Mean Reciprocal Rank). 1 divided by the position of the first correct answer,
averaged. For problems with one right answer.

SILHOUETTE. Clustering metric: how much closer a point is to its own cluster than to the
nearest other one. From -1 to 1.""",
              r"""4. THE CASE THAT CATCHES MOST PEOPLE.

TRAP 1: reporting accuracy on imbalanced data. 1,000 transactions with 10 frauds - a
model predicting "not fraud" for everything scores 990/1000 = 99%. Always compare accuracy
against the majority-class baseline. (Developed fully in the Precision vs Recall sibling.)

TRAP 2 - THE REGRESSION VERSION OF THE SAME MISTAKE: quoting RMSE when MAE is what the
audience means.

    Delivery-time errors in minutes: [2, 3, 1, 4, 60]

        MAE  = (2+3+1+4+60)/5 = 70/5 = 14 minutes
        RMSE = sqrt((4+9+1+16+3600)/5) = sqrt(726) = 26.9 minutes

    Both are correct. They differ by nearly a factor of two, and they say different
    things. MAE says "we are typically off by 14 minutes" - which is nearly true for four
    of the five deliveries. RMSE says 26.9, a number matching NONE of the five errors,
    because the single 60 dominates the squared average.

    Neither is wrong. RMSE is right if one 60-minute failure is much worse than sixty
    1-minute delays - which for a delivery promise it probably is. MAE is right if you
    want to describe typical experience. THE GAP BETWEEN THEM IS ITSELF A DIAGNOSTIC: when
    RMSE is much larger than MAE, you have outliers, and that is worth knowing before you
    pick either.

TRAP 3: MAPE near zero. Predicting demand of 0.5 units and being off by 1 gives a 200%
error; enough near-zero actuals and MAPE becomes meaningless. Note the code guards this
with a clip - which prevents a crash and does NOT make the number trustworthy.

TRAP 4: R-squared always improving. Add a column of random noise as a feature and
R-squared goes UP, because it can only decrease if the new feature is perfectly useless
AND the fit is exact. It never penalises complexity. Use adjusted R-squared, or judge on
held-out data.

TRAP 5: optimising a metric that is not the decision. A team maximises F1 and ships. But
F1 asserts precision and recall matter equally - and if a miss costs twenty-five times a
false alarm, the F1-optimal threshold is simply the wrong point. (The ROC sibling works
that arithmetic in full.)

TRAP 6: ignoring log loss when the PROBABILITY is the product. If downstream systems
multiply the probability by a value to make a bid or a triage decision, then a model that
ranks correctly but is systematically overconfident will lose money while showing an
excellent AUC. AUC cannot see calibration at all - it only sees order.

TRAP 7: comparing metrics across datasets. AUC 0.90 here and 0.85 there does not establish
that the first model is better; separability differs between populations.

TRAP 8: a ranking metric that ignores position. Precision@10 gives the identical score
whether the one relevant result is at position 1 or position 10. If position matters -
and for search it always does - you need NDCG or MRR.""",
              r"""5. THE NAIVE APPROACH FIRST, THEN THE REAL ONE.

THE NAIVE APPROACH: use the default metric for the model type. Accuracy for
classification, R-squared for regression, and move on.

It is what every tutorial reports, so it feels standard. It fails because a metric is not
a neutral description of quality - it is an assertion about what matters, and the defaults
assert things that are usually false:

    ACCURACY asserts   every error costs the same and the classes are balanced.
    RMSE asserts       an error of 10 is a hundred times worse than an error of 1.
    R-SQUARED asserts  explained variance is what you care about, and it silently rewards
                       adding features.
    PRECISION@k asserts position within the top k is irrelevant.

Any of those can be exactly right. The mistake is not choosing them - it is choosing them
without noticing you made a claim.

THE REAL APPROACH: start from the decision, work backwards to the metric.

  1. WHAT DECISION does this prediction drive? Block a card, order stock, show a result,
     alert a doctor.
  2. WHAT DOES EACH KIND OF ERROR COST, in real units? Money, time, harm.
  3. WHICH METRIC HAS THOSE COSTS BUILT INTO IT? If none does, build a cost function
     directly - that is always legitimate and is often better than any named metric.

THE UPGRADE PATH, in increasing sophistication - and the direction to move as you get more
serious about a problem:

    LEVEL 1 - a single default metric. Fast, and asserts something you have not checked.

    LEVEL 2 - the RIGHT named metric for the error costs. Precision when false alarms
    hurt, recall when misses hurt, MAE when typical error is the story, NDCG when position
    matters.

    LEVEL 3 - a CUSTOM COST FUNCTION in real units. total_cost = FP x cost_of_false_alarm
    + FN x cost_of_miss. This is what the code's best_threshold does, and it is strictly
    better than any named metric when you can get the numbers, because it encodes the
    actual objective rather than a proxy for it.

    LEVEL 4 - a CONSTRAINED objective when costs are unavailable: "recall must be at least
    0.95; among the thresholds meeting that, take the highest precision." Encodes a real
    requirement without needing a price list.

WHY NDCG DISCOUNTS BY log2 OF THE POSITION - the trick, from scratch, because it is the
one formula here that looks arbitrary.

You want a ranking metric where being at position 1 is worth more than position 2, which
is worth more than position 3. So divide each item's relevance by something that grows
with position. But how fast should the value fall?

    DIVIDE BY THE POSITION ITSELF (1, 2, 3, 4...): position 2 is worth half of position 1.
    That is a steep drop - it says the second result barely matters, which does not match
    how people actually read a results page.

    DIVIDE BY log2(position + 1)  (1, 1.58, 2, 2.32, 2.58...): position 2 is worth 63% of
    position 1, position 4 is worth 50%, position 8 about 33%. The value decays, but
    gently, and it keeps decaying forever without ever hitting zero.

The logarithm is chosen because it matches observed behaviour - attention falls off with
depth, but a result at position 8 is not worthless. The +1 exists so the first position
gives log2(2) = 1, dividing by one rather than by zero.

Then NORMALISE: compute the same score for the PERFECT ordering of the same items and
divide. That is what turns DCG into NDCG and puts it on a 0-to-1 scale, so scores are
comparable across queries that have different numbers of relevant results.""",
              r"""6. HOW TO CHOOSE - the procedure, step by step.

The one sentence that holds the whole idea: NAME THE DECISION, PRICE EACH KIND OF ERROR,
AND PICK THE METRIC WHOSE ARITHMETIC ALREADY ENCODES THAT PRICING - OR WRITE THE COST
FUNCTION DIRECTLY AND SKIP THE NAMED METRICS ENTIRELY.

THERE IS A LOOP HERE - selecting the metric and then the operating point - and it needs a
stopping rule:

  - Each pass proposes a metric or a threshold, evaluates it on validation data, and
    checks whether the resulting behaviour is what the business actually wants.
  - WHAT MAKES IT STOP: the metric is agreed BEFORE modelling begins, and the operating
    point is then chosen by a fixed objective (minimum cost, or a stated constraint).
  - WHAT MAKES IT NOT TERMINATE: choosing the metric AFTER seeing results. There is
    always some metric under which the current model looks good, and searching for it
    feels like analysis. Fix the metric first; that is the whole discipline.

THE STEPS:

  1. NAME THE DECISION the prediction drives. If nobody can name one, stop - you do not
     have a metric problem, you have a product problem.

  2. IDENTIFY THE OUTPUT SHAPE - class, probability, number, ranked list, clustering. This
     eliminates most of the menu immediately.

  3. GET THE BASE RATE for classification. It determines whether accuracy means anything
     and whether to prefer ROC or PR.

  4. PRICE THE ERRORS in real units. What does a false alarm cost? What does a miss cost?
     For regression: is one big error worse than several small ones, or not?

  5. CHOOSE THE METRIC WHOSE ARITHMETIC MATCHES that pricing, using the routing table in
     section 2.

  6. IF THE PROBABILITIES ARE USED DOWNSTREAM, add log loss or a calibration check. AUC
     is blind to calibration - it only sees order.

  7. FIX THE METRIC BEFORE MODELLING. Write it down. This is what stops the search for a
     flattering number later.

  8. REPORT MORE THAN ONE. A single number always hides something - report precision AND
     recall, or MAE AND RMSE. The gap between two metrics is itself informative (RMSE far
     above MAE means outliers).

  9. CHOOSE THE OPERATING POINT by cost or by constraint, on validation data, never on
     test.

 10. RE-CHECK PERIODICALLY. Base rates drift, and precision moves with them even when the
     model has not changed at all.""",
              r"""7. WHAT IS HAPPENING, told as a story - no jargon at all.

Imagine judging three completely different competitions and being handed the same
scoresheet for all of them.

In the first, a baker must produce a hundred identical rolls. What matters is consistency,
so you measure the average deviation from the target weight. One roll wildly wrong is
about as bad as several slightly wrong - all your customers get one roll each.

In the second, a bridge engineer submits a hundred load calculations. Here one wildly
wrong answer is not like several slightly wrong ones; it is catastrophically worse,
because the bridge falls down once. So you square the errors before averaging, which makes
a single large mistake dominate the score - deliberately.

In the third, a librarian is asked for the ten most useful books on a subject. Now it is
not about how wrong the answers are but about ORDER. Ten good books in a bad order is a
worse answer than the same ten with the best first, because the person asking will read
the first two and leave.

Same word - "how well did they do?" - three genuinely different questions. Handing the
baker's scoresheet to the engineer would pass a bridge that falls down, because the one
disastrous calculation gets averaged away by ninety-nine fine ones.

And there is a fourth situation, the sly one. Suppose someone does not need the librarian's
ordering at all, but needs to know how CONFIDENT she is in each recommendation, because
they are betting money on it. Now a librarian who is always right but says "I'm 99% sure"
about everything, including the ones she gets wrong, is dangerous in a way that no ordering
score can detect. That is what measuring the probabilities rather than the ranking is for.

So the first question is never "what is the score". It is "what is the decision, and what
does it cost me to be wrong in each direction".""",
              r"""8. THE CODE, LINE BY LINE, in the real variable names.

    import numpy as np

    def confusion(y, pred):

y is the array of true labels (1 for positive, 0 for negative); pred is the array of
predicted labels. Returns the four counts. Neither array is modified.

        tp = int(((pred == 1) & (y == 1)).sum());  fp = int(((pred == 1) & (y == 0)).sum())

Read it inside out. `pred == 1` produces an array of True/False, one per item. `y == 1`
likewise. The single `&` is ELEMENTWISE and - True only where both are True at the same
position. `.sum()` counts the Trues, since True counts as 1. So tp is "predicted positive
AND actually positive", and fp is "predicted positive AND actually negative". `int(...)`
converts numpy's integer type to a plain Python one so the returned dictionary prints
cleanly.

        fn = int(((pred == 0) & (y == 1)).sum());  tn = int(((pred == 0) & (y == 0)).sum())

The other two boxes. fn is the misses, tn the correct rejections. These four always sum to
the total, which is the fastest check that a confusion matrix is right.

    def report(y, pred):
        tp, fp, fn, tn = confusion(y, pred)

Unpack the four counts. Every metric below is arithmetic on these.

        precision = tp / (tp + fp) if tp + fp else 0.0     # of flagged, how many real

The guard matters. If NOTHING was flagged, tp + fp is 0 and this would be 0/0. The
convention - and what scikit-learn does, with a warning - is to report 0.0. A model that
flags nothing does not have perfect precision; it has no precision.

        recall    = tp / (tp + fn) if tp + fn else 0.0     # of real, how many caught

Same guard for the case where there are no actual positives at all in the sample.

        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

The harmonic mean. The guard covers precision and recall both being 0, which would
otherwise divide by zero. Note the harmonic mean is 0 whenever either input is 0 - that is
the property that makes it a useful summary, since a model perfect on one axis and useless
on the other should not score halfway.

        return {"accuracy": (tp + tn) / len(y), ...

accuracy uses len(y) as the denominator - the total number of items - which is the same as
tp+fp+fn+tn. Note this is the metric that includes tn, and therefore the one that breaks
under imbalance.

                "specificity": tn / (tn + fp) if tn + fp else 0.0}

specificity is recall's mirror image for the negative class: of everything actually
negative, how much was correctly ignored. It equals 1 - FPR, the quantity on the ROC
curve's horizontal axis.

    y = np.array([0] * 990 + [1] * 10)          # 1% fraud
    always_zero = np.zeros(1000)
    report(y, always_zero)

The 99%-accuracy trap made executable. 990 negatives, 10 positives, and a "model" that
predicts 0 for everything. Traced in section 9.

    def best_threshold(y, probs, cost_fp=1.0, cost_fn=10.0):

probs is the array of predicted PROBABILITIES rather than classes. cost_fp and cost_fn are
what one false alarm and one miss cost, in whatever unit you choose - they only need to be
consistent with each other. The defaults encode "a miss costs ten false alarms".

        best, best_cost = 0.5, float("inf")

Start with the conventional threshold and an impossibly high cost, so the first real
candidate always wins.

        for t in np.linspace(0.01, 0.99, 99):

99 candidate thresholds evenly spaced from 0.01 to 0.99. A finite grid, which is why this
loop terminates - it is a sweep, not a search.

            tp, fp, fn, tn = confusion(y, (probs >= t).astype(int))

`probs >= t` gives True/False per item; `.astype(int)` turns that into 1s and 0s so it can
be fed to confusion. This is where a probability becomes a decision, and it is the only
place the threshold enters.

            cost = fp * cost_fp + fn * cost_fn

The objective, in real units. Note what is ABSENT: tp and tn contribute nothing, because
correct answers cost nothing. Only mistakes are priced.

            if cost < best_cost:
                best, best_cost = t, cost
        return best, best_cost

Keep the cheapest. Strictly-less-than means the first threshold achieving a given cost
wins ties, so the lowest threshold is preferred on a tie - worth knowing if you ever see a
suspiciously low answer.

    def rmse(y, p): return float(np.sqrt(np.mean((y - p) ** 2)))

Errors, SQUARED, averaged, then square-rooted. The squaring is the whole character of this
metric: it makes one error of 10 count as much as a hundred errors of 1. The final
square-root returns it to the target's units, which is what makes it reportable.

    def mae(y, p):  return float(np.mean(np.abs(y - p)))

Absolute errors, averaged. No squaring, so an outlier contributes in proportion to its
size rather than its square. This is the one that supports "we are typically off by X".

    def mape(y, p): return float(np.mean(np.abs((y - p) / np.clip(np.abs(y), 1e-9, None))) * 100)

Percentage error. `np.clip(np.abs(y), 1e-9, None)` forces the denominator to be at least
one billionth, preventing division by zero. Read that guard honestly: it stops a CRASH, it
does not make the answer meaningful. Dividing by 1e-9 produces an astronomically large
percentage that will dominate the mean. If actuals can be near zero, MAPE is the wrong
metric, not a metric needing a guard.

    def r2(y, p):   return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())

One minus (the model's squared error) divided by (the squared error of just predicting the
mean). So 1.0 is perfect, 0 means no better than the mean, and NEGATIVE means worse than
predicting the mean - which is possible and worth knowing.

    def dcg(relevances):
        return sum(r / np.log2(i + 2) for i, r in enumerate(relevances))

Discounted Cumulative Gain. i counts from 0, so the divisor is log2(2) = 1 for the first
item, log2(3) = 1.585 for the second, log2(4) = 2 for the third. Each item's relevance is
divided by that position discount and summed. The +2 is what makes the first position
divide by 1 rather than by log2(1) = 0.

    def ndcg(relevances, k=10):
        ideal = sorted(relevances, reverse=True)[:k]
        return dcg(relevances[:k]) / (dcg(ideal) or 1.0)

`ideal` is the SAME relevance values sorted best-first - the perfect ranking of this exact
result set. Dividing by its DCG normalises to a 0-to-1 scale, so scores are comparable
across queries with different numbers of relevant results. `or 1.0` guards the case where
every relevance is 0, which would make the ideal DCG zero and the division undefined.""",
              r"""9. THE CODE TRACED WITH REAL NUMBERS - AND THE COST OPTIMUM MOVING.

TRACE 1 - report() ON THE 99%-ACCURACY TRAP.

    y = np.array([0]*990 + [1]*10)     990 legitimate, 10 fraudulent
    always_zero = np.zeros(1000)       predict "not fraud" for everything

    confusion(y, always_zero):
        tp = count where (pred==1 AND y==1)  ->  pred is never 1  ->  0
        fp = count where (pred==1 AND y==0)  ->                       0
        fn = count where (pred==0 AND y==1)  ->  all 10 frauds     -> 10
        tn = count where (pred==0 AND y==0)  ->  all 990 legit     -> 990
        check: 0 + 0 + 10 + 990 = 1000  ✓

    report(y, always_zero):
        precision   = tp+fp is 0        -> guard fires -> 0.0
        recall      = 0 / (0 + 10)      -> 0.0
        f1          = precision+recall is 0 -> guard fires -> 0.0
        accuracy    = (0 + 990) / 1000  -> 0.99
        specificity = 990 / (990 + 0)   -> 1.0

    ACCURACY 0.99 AND SPECIFICITY 1.0 - two metrics reporting near-perfection for a model
    containing no logic whatsoever. Recall 0.0 is the only number telling the truth. This
    is why the guards matter too: without them this call would have crashed on 0/0 rather
    than quietly returning 0.

TRACE 2 - best_threshold(), AND THE ANSWER INVERTING ON COST.

    A fraud model over 1,000 transactions with 10 frauds. At four of the 99 candidate
    thresholds the sweep finds:

        threshold     TP    FN     FP
        ---------    ----  ----  -----
          0.3          9     1     210
          0.5          8     2      92
          0.7          6     4      30
          0.9          3     7       5

    With the DEFAULTS, cost_fp = 1 and cost_fn = 10:

        cost = fp * 1 + fn * 10

          0.3:   210 + 10 =  220
          0.5:    92 + 20 =  112
          0.7:    30 + 40 =   70      <-- minimum
          0.9:     5 + 70 =   75

        best_threshold returns (0.7, 70.0).

    NOW CHANGE ONE ARGUMENT. Suppose the business enters a regulated market where an
    undetected fraud also carries a penalty, so cost_fn = 100 instead of 10:

        cost = fp * 1 + fn * 100

          0.3:   210 + 100 =  310
          0.5:    92 + 200 =  292      <-- minimum
          0.7:    30 + 400 =  430
          0.9:     5 + 700 =  705

        best_threshold returns (0.5, 292.0).

    THE MODEL DID NOT CHANGE. THE DATA DID NOT CHANGE. The optimal threshold moved from
    0.7 to 0.5 purely because one cost constant changed - and the system now accepts 92
    false alarms instead of 30, because each miss became ten times dearer.

    That is the argument for level 3 of section 5: a cost function in real units answers
    the question directly, where a named metric can only approximate it.

TRACE 3 - REGRESSION, AND WHY TWO METRICS DISAGREE.

    Delivery-time errors, in minutes: [2, 3, 1, 4, 60]

        mae:  (2 + 3 + 1 + 4 + 60) / 5  =  70 / 5  =  14.0 minutes

        rmse: squares are 4, 9, 1, 16, 3600
              sum = 3630,  mean = 726,  sqrt(726) = 26.94 minutes

    MAE says 14. RMSE says 26.9. Both are correct arithmetic on the same five numbers.

    MAE describes four of the five deliveries well. RMSE matches NONE of the individual
    errors - it is inflated by the single 60, exactly as designed, because squaring makes
    3600 dwarf the other four values combined (which total 30).

    THE RATIO IS ITSELF A DIAGNOSTIC: RMSE nearly twice MAE says there are outliers. If
    the two were close, the errors would be evenly spread.

    WHICH TO REPORT: MAE to a stakeholder who wants to know the typical experience; RMSE
    if one 60-minute failure genuinely matters more than sixty 1-minute delays - which for
    a delivery promise it probably does. Report both, and say why they differ.

TRACE 4 - ndcg(), COMPUTED FULLY.

    ndcg([3, 2, 3, 0, 1, 2]) with the default k = 10.

    The list has 6 items, so relevances[:10] is all of them.

    dcg([3, 2, 3, 0, 1, 2]):
        i=0:  3 / log2(2) = 3 / 1.0000 = 3.0000
        i=1:  2 / log2(3) = 2 / 1.5850 = 1.2619
        i=2:  3 / log2(4) = 3 / 2.0000 = 1.5000
        i=3:  0 / log2(5) = 0 / 2.3219 = 0.0000
        i=4:  1 / log2(6) = 1 / 2.5850 = 0.3869
        i=5:  2 / log2(7) = 2 / 2.8074 = 0.7124
        DCG = 3.0000 + 1.2619 + 1.5000 + 0.0000 + 0.3869 + 0.7124 = 6.8612

    ideal = sorted([3,2,3,0,1,2], reverse=True) = [3, 3, 2, 2, 1, 0]

    dcg([3, 3, 2, 2, 1, 0]):
        i=0:  3 / 1.0000 = 3.0000
        i=1:  3 / 1.5850 = 1.8928
        i=2:  2 / 2.0000 = 1.0000
        i=3:  2 / 2.3219 = 0.8614
        i=4:  1 / 2.5850 = 0.3869
        i=5:  0 / 2.8074 = 0.0000
        IDCG = 3.0000 + 1.8928 + 1.0000 + 0.8614 + 0.3869 + 0.0000 = 7.1411

    NDCG = 6.8612 / 7.1411 = 0.961

    Read what the number means: this ordering captures 96.1% of the value the perfect
    ordering of these same items would have delivered. The main loss is that a relevance-3
    item sits at position 3 instead of position 2, and the relevance-2 item at position 6
    should have been higher.

    AND THE CONTRAST WITH precision@k, which is why ranking needs its own metric:
    precision@6 counts how many of the six are relevant and gives the SAME answer for
    [3,2,3,0,1,2] and for [0,1,2,2,3,3] - the worst possible ordering of the identical
    items. NDCG gives 0.961 for the first and would give roughly 0.79 for the second. Only
    NDCG can see the difference, because only NDCG has a position discount.""",
              r"""10. THE COSTS IN PLAIN WORDS, THE #1 MISTAKE, AND THE TAKEAWAY.

WHAT EACH METRIC COSTS TO COMPUTE, since this occasionally matters at scale:

  - The classification metrics are one pass over the predictions. Free.
  - A threshold sweep is one pass PER CANDIDATE threshold - 99 passes in this code. Still
    cheap, but do it on validation data rather than on everything.
  - ROC-AUC and PR-AUC require sorting by score: O(n log n).
  - NDCG requires sorting the relevances for the ideal ranking, per query.
  - The expensive part is never the arithmetic. It is obtaining the LABELS - and for
    ranking, human relevance judgements, which is why offline ranking evaluation is
    expensive and why teams lean on click data as a noisy proxy.

THE ROUTING SUMMARY - the thing to be able to reproduce under pressure:

    CLASSIFICATION
        balanced, errors equal              accuracy
        false alarms expensive              precision
        misses expensive                    recall
        one number, errors comparable       F1  (F-beta if not comparable)
        ranking quality, balanced           ROC-AUC
        ranking quality, rare positives     PR-AUC
        probabilities used downstream       log loss + a calibration check
    REGRESSION
        outliers matter more                RMSE
        typical error is the story          MAE
        relative error, actuals far from 0  MAPE
        variance explained                  R-squared (adjusted, or held-out)
    RANKING
        only the page matters               precision@k
        position matters                    NDCG
        one right answer                    MRR
    CLUSTERING
        no labels available                 silhouette, Davies-Bouldin

    AND ABOVE ALL OF THEM: if you can price the errors, write the cost function directly.
    It beats every named metric because it encodes the real objective instead of a proxy.

THE INTERVIEW QUESTIONS, WITH THEIR ANSWERS:

  - "Which metric would you use for X?" Never answer immediately. Ask what decision the
    prediction drives and what each error costs. The question is testing whether you reach
    for a default or reason from the problem.
  - "Our model is 99% accurate." Ask the base rate. (Precision vs Recall sibling.)
  - "Our AUC is 0.94, ship it?" Ask the base rate and the operating threshold. (ROC
    sibling.)
  - "Why is RMSE so much higher than MAE?" Outliers. And that is a finding about the data,
    not a problem with the metric.
  - "R-squared went up when we added a feature - is the model better?" Not necessarily.
    R-squared never decreases when features are added. Check on held-out data or use
    adjusted R-squared.
  - "The model ranks well but our bidding system loses money." Calibration. AUC sees only
    order, not whether a 0.7 really means 70%. Measure log loss and plot a calibration
    curve.

THE #1 MISTAKE: choosing the metric AFTER seeing the results. There is always some metric
under which the current model looks good, and hunting for it feels like analysis while
being the opposite. Fix the metric before modelling, write it down, and report more than
one number so a single figure cannot hide the failure mode.

RUNNER-UP: reporting one number at all. Precision without recall, or RMSE without MAE,
each conceals exactly the thing the other would reveal.

TAKEAWAY: a metric is a claim about what errors cost, not a neutral measure of quality -
so name the decision, price the mistakes in real units, and pick the metric whose
arithmetic already encodes that pricing, or write the cost function yourself and skip the
named metrics entirely.""",
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
          examples=[
              "The sample-size calculation, with the number that decides whether to run at all. 5% baseline conversion, wanting to detect a 10% relative lift at 80% power: about 31,000 users PER ARM. Halve the effect you want to detect and it becomes ~124,000 - four times as many, because the required n scales with 1/effect². That relationship is the useful one: if the team wants to detect a 2% lift on a page with 5,000 weekly visitors, the honest answer is that the experiment would take months and is not worth running. Computing this BEFORE starting is what separates an experiment from a hope.",
              "Peeking, quantified. Checking once at alpha = 0.05 gives a 5% false-positive rate by construction. Checking daily for two weeks and stopping at the first significant result pushes the real false-positive rate past 20% - because each look is a fresh chance to be fooled by noise, and you stop precisely when noise favours you. The fixes: fix the duration in advance and do not look, or use a sequential test (always-valid p-values, or a Bayesian approach) designed for continuous monitoring. 'We saw significance on day 3 so we shipped' is the most common way teams ship nothing.",
              "Sample ratio mismatch, the check that comes before any analysis. You asked for a 50/50 split and got 48,000 / 52,000. That is a chi-squared p-value of essentially zero on those counts - the assignment or the logging is broken, and the result is not interpretable at all. Common causes: a bot filter applied to one arm, a redirect that fails more often in treatment, or an SDK that drops events under load. Always run this check first; a beautiful lift on mismatched arms is a bug report, not a win.",
              "The offline/online disagreement that motivates the whole exercise. A new ranking model improves offline NDCG by 4%; the A/B test shows flat clicks and a 3% DROP in sessions. Investigation: the model favours long-form content, which takes longer to consume, so users see fewer items per session. The offline metric measured ranking quality; the experiment measured the product. Neither was wrong - they measured different things, and only one of them is what the business is paying for. This is why shipping decisions are made online.",
              "Guardrails, decided before you see results. A recommender that lifts click-through 8% while adding 200ms of p99 latency and raising unsubscribes 3% is a LOSS. Typical guardrail set: p99 latency must not rise more than 10%, error rate must not rise at all, revenue per user must not fall, unsubscribe rate must not rise. Writing these down in advance is what stops the post-hoc argument where whoever built the model decides which metrics count.",
              "The ML-specific wrinkles that break naive experiments. INTERFERENCE: a recommender in treatment changes what control users see through shared inventory, so the arms are not independent - switchback or geo-based designs handle this. DELAYED FEEDBACK: a conversion may take days, so a one-week test undercounts treatment's effect. FEEDBACK LOOPS: the model influences the data it will next be trained on, so a lift can be self-reinforcing rather than real. And novelty effects - a change often looks good in week one purely because it is new, which is why you run at least one full weekly cycle.",
          ],
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
