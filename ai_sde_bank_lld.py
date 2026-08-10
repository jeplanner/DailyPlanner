"""Low-level / OOP design pack for the AI SDE bank (Section 5).

Amazon runs an explicit object-oriented-design round for SDE-1 ("design a
parking lot / an elevator / a vending machine"); Google folds the same skill
into the coding rounds ("now make it support three payment types"). Neither
wants a UML diploma - they want to see you turn a vague sentence into a few
well-named classes, defend the boundaries between them, and leave one obvious
place to extend.

Imported by ai_sde_bank.py, which passes in its Q(...) constructor so these
entries pick up tags, difficulty, prep_minutes and the stack rank like the
rest of the bank. Every entry is written for a final-year student: plain
English first, then the class code, then the trap that sinks most candidates.
"""


def _c(s):
    """Trim the leading/trailing newlines off a triple-quoted code block."""
    return s.strip("\n")


def build(Q):
    entries = []

    # ── Foundations: how to actually drive the round ──────────────────────
    entries += [
        Q("lld", "How to drive a low-level design (LLD) interview",
          "An LLD prompt is deliberately one sentence long ('design a parking lot'). The interviewer is watching whether you can impose structure on that vagueness. Run the same five moves every single time. (1) CLARIFY AND SHRINK - ask two or three questions and then state the scope you will build out loud: 'I'll support multiple vehicle sizes, hourly pricing, and one payment method; I'll skip reservations and multi-floor routing unless you want them.' Fixing scope yourself is a strong signal - it is the thing juniors never do. (2) NOUNS BECOME CLASSES - read the problem back and underline the nouns: parking lot, floor, spot, vehicle, ticket, payment. Those are your candidate classes. Drop the ones that are just data on another class. (3) VERBS BECOME METHODS - park, unpark, price, pay. Put each verb on the class that owns the data it needs. (4) DRAW THE RELATIONSHIPS - who holds a reference to whom, and is it has-a (composition, the default) or is-a (inheritance, only for genuine substitutability). (5) NAME THE EXTENSION POINT - say out loud 'the pricing rule is the thing most likely to change, so it goes behind a PricingStrategy interface' and put exactly one interface there. Then write real code for the two or three interesting classes, not skeletons for all ten. Talking through all five moves takes four minutes and buys you the rest of the hour.",
          ["lld", "framework", "ood", "interview-strategy"],
          difficulty="Easy",
          frequency="Applies to every OOD round - Amazon SDE-1 loops almost always contain one.",
          mnemonic="Nouns -> classes. Verbs -> methods. Has-a beats is-a. One interface at the thing that will change. Say your scope out loud before you write a line.",
          example="Prompt: 'Design a vending machine.' Thirty seconds later you should be saying: 'Nouns - Machine, Product, Slot, Coin, Payment. Verbs - selectProduct, insertCoin, dispense, refund. The machine is a state machine (Idle -> HasMoney -> Dispensing), so State is my extension point. I'll skip restocking and the admin panel unless you want them.'",
          pitfalls="Drawing twelve empty classes instead of writing three real ones; asking zero clarifying questions; inventing a database and a REST API when nobody asked for one (that is high-level design, a different round); using inheritance for everything.",
          followups="'Now add a second payment method' - if your design was right this is a new class, not an edit to an existing one. 'Make it thread-safe' - see the concurrency entry.",
          code=_c('''
# A 60-second skeleton that works for almost any LLD prompt.
from abc import ABC, abstractmethod   # ABC = "Abstract Base Class"
from enum import Enum                 # Enum = a fixed set of named values

class Status(Enum):        # Enums beat magic strings: typo-proof and self-documenting
    AVAILABLE = "available"
    OCCUPIED = "occupied"

class PricingStrategy(ABC):           # <- the ONE extension point
    @abstractmethod                   # subclasses MUST implement this
    def price(self, hours): ...

class HourlyPricing(PricingStrategy): # one concrete rule...
    def __init__(self, rate): self.rate = rate
    def price(self, hours): return self.rate * hours

class FlatPricing(PricingStrategy):   # ...and a second one, added without
    def __init__(self, fee): self.fee = fee   # touching any existing class
    def price(self, hours): return self.fee

class Lot:                            # the "service" class that ties it together
    def __init__(self, pricing):
        self.pricing = pricing        # HAS-A a strategy (composition)
    def checkout(self, hours):
        return self.pricing.price(hours)   # delegates - Lot never asks "which rule?"
'''),
          examples=[
              "Scoping out loud, in practice. Prompt: 'Design a library management system.' Weak start: silently drawing Book, Member, Librarian, Shelf, Rack, Fine, Reservation, Review, Author, Publisher. Strong start: 'I'll cover searching the catalogue, borrowing and returning with a per-member limit, and overdue fines. I'll leave out reservations and inter-branch transfers - tell me if you want them instead.' You have now defined a problem you can finish in 45 minutes, and the interviewer can steer you if they wanted something else. Scope control is graded.",
              "Nouns are candidates, not conclusions. In 'design a parking lot', 'colour' is a noun but it is an attribute of Vehicle, not a class. 'Entrance' is a noun and IS worth a class if entries are gated and ticketed, but is noise if the prompt never mentions gates. The filter: does this thing have behaviour, or its own lifecycle, or a list of things hanging off it? If it is just a value, it is a field.",
              "Verbs go where the data is. A common junior mistake is a fat manager class: ParkingLotManager.calculateFee(ticket), ParkingLotManager.assignSpot(vehicle), ParkingLotManager.printReceipt(ticket) - every method reaching into other objects' fields. Ask 'whose data does this need?' and move it there. Fee calculation needs the ticket's timestamps, so the pricing lives near the ticket. This is the Tell-Don't-Ask principle and it is the difference between OO code and a script with classes.",
              "Finding the extension point. Ask 'if the business changed one thing next quarter, what would it be?' Parking lot -> the pricing rules. Vending machine -> the payment methods. Notification service -> the channels. Elevator -> the dispatch algorithm. That answer is exactly where your one interface goes. Putting interfaces everywhere else is over-engineering, and interviewers do notice.",
              "What 'write real code' means. With 25 minutes left, do not produce ten classes with `pass` in every method. Produce Spot, Ticket and the pricing strategy fully - constructors, the actual fee arithmetic, the error case where a ticket is scanned twice - and describe the rest in a sentence. One working slice beats a complete-looking sketch that does nothing, because the interviewer can only grade code that exists.",
              "The follow-up is the real test. Almost every LLD round ends with 'now support X'. If X requires editing a big if/elif chain in the middle of your core class, your design failed the Open/Closed principle and the interviewer just saw it happen live. If X is a new subclass registered in one place, you pass. So when you design, imagine the follow-up before it is asked - it is nearly always a new variant of the thing you already have two of.",
          ]),

        Q("lld", "SOLID principles - all five, each with the bug it prevents",
          "SOLID is five rules for where to draw class boundaries. Learn them as five specific bugs. (S) SINGLE RESPONSIBILITY - a class should have one reason to change. A User class that validates a password, saves to Postgres and formats an HTML email changes when security policy changes, when the schema changes, and when marketing changes the template: three teams editing one file, three chances to break the others. Split it. (O) OPEN/CLOSED - open for extension, closed for modification. If adding a new shape means editing a `if shape == 'circle' ... elif shape == 'square'` chain inside AreaCalculator, then every new shape risks breaking existing shapes. Make each shape implement area() instead: you ADD a file rather than EDIT one. (L) LISKOV SUBSTITUTION - anywhere the base type works, a subclass must work too. The classic violation is Square extends Rectangle: code that does rect.setWidth(5); rect.setHeight(4); assert area == 20 silently breaks when handed a Square. If a subclass has to throw NotSupported or quietly ignore a method, the inheritance is wrong. (I) INTERFACE SEGREGATION - many small interfaces beat one fat one. If your Worker interface demands work() and eat(), a RobotWorker is forced to implement eat() with an exception. Split into Workable and Feedable. (D) DEPENDENCY INVERSION - depend on abstractions, not concrete classes. OrderService should hold a PaymentGateway interface, not `new StripeClient()`, so tests can inject a fake and next year's provider swap touches one line.",
          ["solid", "oop", "principles", "design", "lld"],
          difficulty="Medium",
          frequency="Very commonly asked - either directly ('explain SOLID') or implicitly, as the rubric your design is graded against.",
          mnemonic="S-O-L-I-D as five bugs: one class doing three jobs (S), an if/elif chain that grows forever (O), a subclass that breaks its parent's promise (L), an interface forcing dead methods (I), and `new ConcreteThing()` buried where you cannot mock it (D).",
          code=_c('''
# (O) Open/Closed - the before-and-after that makes SOLID click.

# BEFORE: every new shape means EDITING this function. Touching working code
# to add a feature is how regressions happen.
def area(shape):
    if shape.kind == "circle":
        return 3.14159 * shape.r ** 2
    elif shape.kind == "square":
        return shape.side ** 2
    # ...and a new elif forever. Miss one and you get a silent None.

# AFTER: each shape owns its own formula. Adding Triangle ADDS a class and
# edits nothing that already works.
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self): ...          # the contract every shape must honour

class Circle(Shape):
    def __init__(self, r): self.r = r
    def area(self): return 3.14159 * self.r ** 2

class Square(Shape):
    def __init__(self, side): self.side = side
    def area(self): return self.side ** 2

class Triangle(Shape):           # <- the new feature. Nothing above changed.
    def __init__(self, b, h): self.b, self.h = b, h
    def area(self): return 0.5 * self.b * self.h

def total_area(shapes):
    return sum(s.area() for s in shapes)   # works for shapes that do not exist yet


# (D) Dependency Inversion - the version you can actually test.
class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, amount): ...

class StripeGateway(PaymentGateway):
    def charge(self, amount): ...      # real network call

class FakeGateway(PaymentGateway):     # used by tests - no network, no card
    def __init__(self): self.charges = []
    def charge(self, amount): self.charges.append(amount); return True

class OrderService:
    def __init__(self, gateway: PaymentGateway):   # INJECTED, not constructed
        self.gateway = gateway
    def place(self, order):
        return self.gateway.charge(order.total)

# Test: OrderService(FakeGateway()) - runs in a millisecond, offline.
'''),
          pitfalls="Reciting the acronym without an example (interviewers hear this all day); applying SOLID to a 20-line script and calling three-classes-for-one-job 'clean'; confusing Single Responsibility with 'one method per class'.",
          followups="'Which one do you break most often, and when is that fine?' - a good answer names Single Responsibility in early-stage code, where premature splitting slows you down. 'Show me a Liskov violation you have actually seen.'",
          examples=[
              "Single Responsibility, made concrete. A Report class with generate(), saveToPdf() and emailToManager() has three reasons to change: the business logic, the PDF library, and the mail provider. Six months later the PDF library has a breaking upgrade and you are editing the file that also contains your revenue arithmetic, with the reviewer unable to tell the two apart. Split into ReportBuilder, PdfWriter and Mailer and each change touches one small, separately-testable file.",
              "Open/Closed in a notification service. Version 1 has send(user, msg) with `if channel == 'email' ... elif channel == 'sms'`. Version 2 adds push, version 3 adds WhatsApp, and now that one method is 200 lines that every channel team must edit and re-test. With a Channel interface plus EmailChannel, SmsChannel, PushChannel, each team owns a file and the dispatcher becomes `self.channels[name].send(...)` - one line that never changes again.",
              "Liskov, the rectangle/square trap in full. Rectangle has setWidth and setHeight. Square inherits and overrides both to keep the sides equal - which sounds sensible. Now existing code `r.setWidth(5); r.setHeight(4); assert r.area() == 20` passes for Rectangle and fails for Square, even though the code never mentions Square. Nothing in Square is buggy in isolation; the inheritance CLAIM ('a square can be used anywhere a rectangle can') is false because rectangles promise independently settable sides. Fix: make both implement a Shape interface with an immutable area(), no inheritance between them.",
              "Interface Segregation with a real smell. A Printer interface with print(), scan(), fax() forces a cheap ink-jet class to implement scan() and fax() as `raise NotImplementedError`. Any caller holding a Printer now has to guess which methods actually work - the type system is lying. Split into Printable, Scannable, Faxable; the multifunction device implements all three, the cheap printer implements one, and the caller's type tells the truth.",
              "Dependency Inversion is mostly a testing principle. If OrderService does `self.gateway = StripeClient(api_key)` inside its constructor, then testing 'does a declined card roll back the order?' requires a real Stripe sandbox, a network, and a card that reliably declines - so in practice nobody writes that test. Inject the gateway and the same test is three lines with a fake that returns False. When an interviewer asks 'how would you test this?', DIP is the answer you are reaching for.",
              "When to deliberately break SOLID. A 40-line internal script that runs nightly does not need five files and an interface. The rules buy you cheap change later at the cost of indirection now, and indirection is not free - it costs a reader a jump to a second file. Say this out loud in the interview: 'I'd keep this as one class today, and split it the moment we have a second payment provider.' Judgement about WHEN to apply a principle scores higher than applying it everywhere.",
          ]),

        Q("lld", "Composition over inheritance - why 'is-a' keeps failing",
          "In plain words: inheritance means 'this thing IS a kind of that thing and can be used anywhere that thing can'. Composition means 'this thing HAS a helper it delegates to'. Beginners reach for inheritance because it removes duplicate code fastest, and it is usually the wrong tool. Three concrete reasons. (1) Inheritance is a promise, not a shortcut - saying Penguin extends Bird commits you to Penguin working anywhere a Bird works, including bird.fly(). The moment a subclass has to override a method into a no-op or an exception, the promise is broken. (2) One axis only - if you have Cars that vary by engine (petrol, electric) AND by roof (hardtop, convertible), inheritance forces you to pick one axis to subclass and you end up with PetrolHardtopCar, PetrolConvertibleCar, ElectricHardtopCar... a class explosion of size m x n. Composition gives you a Car that HAS an Engine and HAS a Roof: m + n classes, and any combination works. (3) Inheritance is fixed at compile time; composition can change at runtime. A Duck that HAS a FlyBehaviour can be handed a rocket mid-flight; a Duck that EXTENDS FlyingBird cannot. The practical rule: use inheritance only when the subclass is genuinely substitutable and you are sharing an INTERFACE, not just code. If you only wanted to share code, make a helper object and delegate to it.",
          ["composition", "inheritance", "oop", "lld", "design"],
          difficulty="Medium",
          frequency="Very commonly asked at Amazon and Google as a direct OOP question and as the follow-up to any design where you used inheritance.",
          mnemonic="Ask 'IS it one, or does it HAVE one?' If you would ever need to disable an inherited method, you wanted HAS-A. Inheritance = a promise of substitutability; composition = a rented helper you can swap at runtime.",
          code=_c('''
# The class explosion, and the fix. Ducks that differ in HOW they fly and
# HOW they sound - the textbook case (from Head First Design Patterns).

# WRONG: inheritance on two axes at once.
# class Duck: ...
# class FlyingQuackingDuck(Duck): ...
# class FlyingMuteDuck(Duck): ...
# class RubberDuck(Duck):
#     def fly(self): raise NotImplementedError   # <- the tell-tale sign

# RIGHT: pull each varying behaviour into its own small family, and HAVE one.
from abc import ABC, abstractmethod

class FlyBehaviour(ABC):
    @abstractmethod
    def fly(self): ...

class FlyWithWings(FlyBehaviour):
    def fly(self): return "flies away"

class CannotFly(FlyBehaviour):        # a real, honest behaviour - not an exception
    def fly(self): return "stays put"

class QuackBehaviour(ABC):
    @abstractmethod
    def quack(self): ...

class Quack(QuackBehaviour):
    def quack(self): return "Quack!"

class Squeak(QuackBehaviour):
    def quack(self): return "Squeak!"

class Duck:
    # The duck HAS-A fly behaviour and HAS-A quack behaviour.
    def __init__(self, fly: FlyBehaviour, quack: QuackBehaviour):
        self._fly, self._quack = fly, quack

    def perform_fly(self):   return self._fly.fly()      # delegate, do not decide
    def perform_quack(self): return self._quack.quack()

    def set_fly(self, behaviour):     # swap at RUNTIME - impossible with inheritance
        self._fly = behaviour

mallard = Duck(FlyWithWings(), Quack())
rubber  = Duck(CannotFly(),   Squeak())    # no exception, no dead method
rubber.set_fly(FlyWithWings())             # someone glued a rocket on it
# 2 fly behaviours x 2 quack behaviours = 4 combinations from 4 small classes,
# not 4 subclasses - and 3 x 3 would be 6 classes instead of 9.
'''),
          pitfalls="Using inheritance purely to avoid retyping a method (that is code reuse, not an is-a relationship); deep hierarchies (three or more levels) where you have to read four files to know what a method does; overriding a method to do nothing.",
          followups="'When IS inheritance right?' - when subclasses are genuinely interchangeable and share a contract, e.g. every Shape has area(). 'What is the diamond problem?' - see the multiple-inheritance/MRO entry in CS Fundamentals.",
          examples=[
              "The exception smell in one line. If a subclass method body is `raise NotImplementedError` or `pass` purely to cancel something it inherited, the hierarchy is wrong. Ostrich extends Bird then kills fly(); RubberDuck extends Duck then kills fly(); ReadOnlyList extends List then kills add(). In every case some caller holding the base type will call the cancelled method and get a runtime surprise the type system promised could not happen.",
              "Counting the explosion. Coffee shop with 3 sizes, 4 milk types and 5 syrups. Inheritance gives 3 x 4 x 5 = 60 classes (SmallOatVanillaLatte...). Composition gives a Drink that HAS a size, a milk and a list of syrups: 3 + 4 + 5 = 12 small pieces and every combination free, including ones nobody enumerated. This is exactly the Decorator pattern's motivation, and it is worth saying the number out loud in an interview.",
              "Runtime swapping wins real features. A game character EXTENDS Wizard cannot become a Warrior mid-game - its class is fixed at construction. A character that HAS-A WeaponBehaviour can pick up a sword and become effective with it instantly: `player.set_weapon(SwordBehaviour())`. Any requirement containing the words 'change while running' or 'configurable' is telling you to compose.",
              "Fragile base class, the maintenance cost. A base class's internal call between its own methods is invisible to subclass authors. Java's Vector had addAll() call add() internally; a subclass that overrode add() to count elements got double counts from addAll(). Nobody wrote a bug - the base class changed an internal detail and every subclass silently broke. Composition has no such coupling: you only see the public methods you chose to call.",
              "Where inheritance genuinely belongs. Shape -> Circle/Square/Triangle is right: every subclass truly IS a shape, every one implements area() meaningfully, and code that computes total area is honestly indifferent to which it gets. Similarly Exception -> ValidationError. The tell is that the base class is mostly an INTERFACE (a contract) with little or no state, and no subclass ever needs to cancel anything.",
              "Python makes the swap cheap, which is why it is worth doing. Because Python is duck-typed, your Duck does not even need the abstract base classes - any object with a fly() method works. That is a feature in an interview: you can say 'strictly I only need the protocol, but I'll declare the ABC so the contract is explicit and mypy can check it'. Showing you know the difference between a nominal type and a structural one is a senior-sounding remark from a new grad.",
          ]),

        Q("lld", "UML relationships you actually need: association, aggregation, composition, inheritance",
          "You will never be asked to draw formal UML, but you will be asked 'what is the relationship between these two classes?' and there are only four answers worth knowing. ASSOCIATION - 'knows about'. A Student knows about a Course; either can exist alone and neither owns the other. Drawn as a plain line, implemented as a reference field. AGGREGATION - 'has, but does not own'. A Team has Players; delete the team and the players still exist and can join another team. Drawn with a hollow diamond, implemented as a list of references passed IN from outside. COMPOSITION - 'has, and owns the lifecycle'. A House has Rooms; demolish the house and the rooms are gone - a room cannot exist independently or be moved to another house. Drawn with a filled diamond, implemented by constructing the parts INSIDE the parent's constructor. INHERITANCE - 'is a'. A Circle is a Shape. Drawn with a hollow triangle arrow, implemented with `class Circle(Shape)`. The one distinction interviewers actually probe is aggregation vs composition, and the test is a single question: if I delete the container, should the contents die with it? Yes = composition, no = aggregation. Also know MULTIPLICITY - the 1, 0..1, 1..* on the line - because 'can a spot hold more than one vehicle?' is a scoping question you should answer before coding.",
          ["uml", "oop", "relationships", "lld", "design"],
          difficulty="Easy",
          frequency="Commonly asked as a quick check inside an OOD round, especially at Amazon and at Indian campus interviews.",
          mnemonic="Delete the container - do the contents die? Yes = COMPOSITION (filled diamond, House-Room). No = AGGREGATION (hollow diamond, Team-Player). Just points at it? ASSOCIATION. Is a kind of it? INHERITANCE.",
          code=_c('''
class Player:
    def __init__(self, name): self.name = name

class Room:
    def __init__(self, area): self.area = area

class Team:
    """AGGREGATION: players are handed IN and outlive the team."""
    def __init__(self, players):
        self.players = players        # references we did not create

class House:
    """COMPOSITION: rooms are created HERE and die with the house."""
    def __init__(self, sizes):
        self.rooms = [Room(a) for a in sizes]   # we own their lifecycle

class Student:
    """ASSOCIATION: just knows about some courses."""
    def __init__(self, name): self.name, self.courses = name, []
    def enrol(self, course): self.courses.append(course)   # a plain reference

# Multiplicity, stated in words because that is what an interviewer wants:
#   Team  1  ----  1..*  Player     "a team has one or more players"
#   House 1  *--   1..*  Room       "a house owns one or more rooms"
#   Student *  --  *     Course     "many students take many courses"
'''),
          example="Parking lot: a Floor OWNS its Spots (composition - remove the floor and those spots cease to exist), a Spot merely REFERENCES the Vehicle currently in it (association - the car existed before and drives away after), and ElectricSpot IS-A Spot (inheritance).",
          pitfalls="Calling everything composition; drawing arrows without saying what they mean; forgetting multiplicity, which is where the interesting constraints hide ('can one ticket cover two vehicles?').",
          followups="'Many-to-many - how do you implement it?' Usually a third class carrying the relationship's own data (Enrollment holds student, course, grade, date). 'Which direction is the reference?' Prefer one-way unless you truly need to navigate both ways, because two-way references must be kept in sync."),

        Q("lld", "Writing thread-safe classes for an LLD round",
          "Almost every LLD round ends with 'now two people book the last seat at the same time - what happens?'. You do not need deep concurrency theory, you need four moves. (1) NAME THE RACE precisely: 'two threads both read seats_left == 1, both see it is greater than zero, both decrement, and we sell two seats' - the check-then-act gap is where every one of these bugs lives. (2) SHRINK THE SHARED STATE - anything immutable (a frozen price list, a value object) needs no protection at all, so the first fix is often to make fields read-only after construction. (3) LOCK THE SMALLEST THING that covers the whole check-and-act, not the whole method: one lock per Seat lets different seats book in parallel, while one lock on the whole Theatre serialises the entire building. (4) SAY WHAT YOU GAVE UP - locks cost throughput and can deadlock if two are taken in different orders, so state the lock ORDERING rule when you use more than one. The alternatives worth naming: an atomic compare-and-swap or a database `UPDATE ... WHERE status = 'free'` that returns a row count (let the database do the locking - one round trip, no application lock), and an optimistic version column that fails the loser and makes them retry.",
          ["concurrency", "thread-safety", "locks", "lld", "design"],
          difficulty="Hard",
          frequency="Very commonly asked as the closing follow-up to a booking/inventory/parking LLD at Amazon.",
          mnemonic="Every race is a CHECK-THEN-ACT gap. Put the check and the act inside the same lock, make the lock as small as the contended thing, and say the ordering rule if there are two.",
          code=_c('''
import threading

# BROKEN: the classic check-then-act race.
class Counter:
    def __init__(self, n): self.n = n
    def take(self):
        if self.n > 0:        # thread A checks (n == 1) ...
            self.n -= 1       # ... thread B checks too, and BOTH decrement -> n = -1
            return True
        return False

# FIXED: one lock covering the check AND the act.
class SafeCounter:
    def __init__(self, n):
        self.n = n
        self._lock = threading.Lock()      # the door around the shared state
    def take(self):
        with self._lock:                   # only one thread inside at a time
            if self.n > 0:
                self.n -= 1
                return True
            return False


# BETTER for a booking system: lock PER SEAT, so different seats do not queue
# behind each other. Fine-grained locking = more parallelism.
class Seat:
    def __init__(self, seat_id):
        self.id, self.booked = seat_id, False
        self.lock = threading.Lock()

class Theatre:
    def __init__(self, seat_ids):
        self.seats = {s: Seat(s) for s in seat_ids}

    def book(self, seat_id, user):
        seat = self.seats[seat_id]
        with seat.lock:                    # only contends with the SAME seat
            if seat.booked:
                return False               # someone beat us by microseconds
            seat.booked, seat.owner = True, user
            return True

    def book_many(self, seat_ids, user):
        # DEADLOCK RULE: always take multiple locks in a fixed global order
        # (here: sorted by id). Two users grabbing seats 3 and 7 in opposite
        # orders would otherwise wait on each other forever.
        for sid in sorted(seat_ids):
            ...
'''),
          pitfalls="Slapping one global lock on everything and calling it done (correct, but it destroys throughput - say so); locking around the read but not the write; taking two locks in different orders in different methods (deadlock); assuming Python's GIL makes `self.n -= 1` atomic - it is not, it compiles to load/subtract/store.",
          followups="'What if there are two servers?' In-process locks stop working - you need the database (a conditional UPDATE or SELECT ... FOR UPDATE) or a distributed lock with a lease and a fencing token. 'Optimistic vs pessimistic?' Optimistic (version column, retry on conflict) wins when conflicts are rare, which is the usual case for seat booking.",
          examples=[
              "The race, at the level of machine steps. `self.n -= 1` is three operations: read n into a register, subtract one, write it back. Thread A reads 1, is descheduled, thread B reads 1, subtracts, writes 0; thread A resumes with its stale 1, subtracts, writes 0. Two bookings, one decrement. Nothing about Python protects you here - the GIL guarantees one bytecode at a time, and this is three bytecodes.",
              "Lock granularity, with numbers. One lock on the whole Theatre: 1,000 concurrent booking requests all serialise, and if each hold is 2ms the last user waits two seconds. One lock per Seat: only requests for the SAME seat contend, so the popular seat has a short queue and the other 199 seats book in parallel. The cost is 200 lock objects instead of one - trivial memory for a large throughput win. Being able to discuss this trade is what separates a good answer from 'I added synchronized'.",
              "Deadlock from lock ordering, made concrete. User X books seats {7, 3} and locks 7 then 3. User Y books {3, 7} and locks 3 then 7. X holds 7 and waits for 3; Y holds 3 and waits for 7; neither ever proceeds and the threads are gone until the process restarts. The fix costs one word: sort the seat ids before locking, so everyone acquires in the same global order and a cycle is impossible.",
              "Push it into the database when you can. `UPDATE seats SET user_id = :u WHERE id = :s AND user_id IS NULL` returns 1 if you won and 0 if you lost, in a single atomic statement with no application lock at all. This works across many servers, survives a process crash mid-booking, and is usually the right production answer. Saying 'the cleanest lock here is the one the database already has' is a strong senior-flavoured remark.",
              "Immutability removes the problem instead of managing it. A PriceList that is built once and never mutated can be shared by a thousand threads with zero locks, because a race requires a write. In practice a large share of concurrency bugs disappear by making value objects read-only (frozen dataclasses, final fields) and confining every mutation to one small owner class. Mention this first - 'the cheapest thread-safety is having nothing to protect' - before you reach for a lock.",
              "Optimistic concurrency, and why booking systems like it. Give the row a version number. Read seat (version 4), and write with `WHERE version = 4`; the winner bumps it to 5, the loser's update matches zero rows and is told to retry. No one blocks anyone, which is ideal when 99.9% of bookings do not collide. The trade is that under heavy contention for one hot seat, retries burn work - so the general rule is optimistic for rare conflicts, pessimistic locking for constant ones.",
          ]),
    ]

    # ── The design patterns that actually show up in an SDE-1 round ───────
    entries += [
        Q("lld", "Pattern: Strategy - swap an algorithm at runtime",
          "In plain words: pull the part that VARIES into its own little class, and let the main object hold one of them and delegate. Use it whenever you catch yourself writing `if type == A ... elif type == B` to choose behaviour. The main class stops knowing the variants exist - it just calls strategy.do(). Formally: define a family of interchangeable algorithms behind a common interface, and let the client pick one at runtime. This is the single most useful pattern in an LLD interview because the follow-up is nearly always 'now support another pricing rule / payment method / sorting order', and Strategy makes that a new class rather than an edit. The give-away words in a prompt are 'different ways to', 'configurable', 'depending on the customer', and any list of things that all do the same job differently.",
          ["strategy", "pattern", "design-patterns", "lld", "oop"],
          difficulty="Easy",
          frequency="Very commonly asked - the most-used pattern in OOD rounds at Amazon and Google.",
          mnemonic="Strategy = a plug-in algorithm. If you see an if/elif chain PICKING a behaviour, that chain is a Strategy waiting to be extracted.",
          code=_c('''
from abc import ABC, abstractmethod

class ShippingStrategy(ABC):
    @abstractmethod
    def cost(self, weight_kg, distance_km): ...

class StandardShipping(ShippingStrategy):
    def cost(self, weight_kg, distance_km):
        return 5 + 0.5 * weight_kg          # cheap and slow

class ExpressShipping(ShippingStrategy):
    def cost(self, weight_kg, distance_km):
        return 15 + 1.2 * weight_kg + 0.05 * distance_km

class FreeShipping(ShippingStrategy):        # added later. Nothing else changed.
    def cost(self, weight_kg, distance_km):
        return 0

class Order:
    def __init__(self, weight, distance, shipping: ShippingStrategy):
        self.weight, self.distance = weight, distance
        self.shipping = shipping             # HAS-A a strategy
    def total(self, item_price):
        # Order never asks "which shipping is this?" - it just delegates.
        return item_price + self.shipping.cost(self.weight, self.distance)
    def set_shipping(self, s):
        self.shipping = s                    # swap at runtime (user changes their mind)

o = Order(2, 300, StandardShipping())
o.total(100)                                  # 106.0
o.set_shipping(ExpressShipping()); o.total(100)   # 132.4
'''),
          example="Sorting is Strategy in the standard library: `sorted(people, key=lambda p: p.age)` - the comparison rule is injected, so sorted() supports orderings its authors never imagined.",
          pitfalls="Creating a strategy class for something that will only ever have one implementation; leaking variant-specific data into the shared interface (if one strategy needs a coupon code and the others do not, pass a context object rather than widening every signature).",
          followups="'How does the caller choose the strategy?' Usually a small factory or a registry dict mapping a name to a class - that keeps the if/elif in exactly one place instead of scattered. 'Strategy vs State?' Same shape; Strategy is chosen by the client and rarely changes, State is changed by the object itself as events arrive."),

        Q("lld", "Pattern: Factory and Factory Method - centralise object creation",
          "In plain words: instead of scattering `new Circle()` / `new Square()` across your code, you ask one place - the factory - for the object you want, and it decides which concrete class to build. Why bother? Because construction knowledge is a dependency: if fifty files call `StripeClient(api_key, region, retries)` directly, then changing that constructor, or adding a PayPal option, means editing fifty files. Route it through one factory and you edit one. Two flavours worth knowing. SIMPLE FACTORY - a single function or static method with the if/elif (or better, a registry dict) that returns the right subclass; not technically a Gang-of-Four pattern but it is what you will actually write. FACTORY METHOD - the base class defines `create_x()` as abstract and each subclass decides what to build, so the base algorithm works with products it has never heard of. In an LLD interview, a factory is what you point to when the interviewer asks 'where does the if/elif live in your design?' - the honest answer is that it lives in one factory, deliberately, and nowhere else.",
          ["factory", "pattern", "design-patterns", "lld", "oop", "creational"],
          difficulty="Easy",
          frequency="Very commonly asked - pairs with Strategy in almost every OOD answer.",
          mnemonic="Factory = one doorway for construction. The if/elif does not disappear, it gets QUARANTINED in one file so the other fifty stay clean.",
          code=_c('''
from abc import ABC, abstractmethod

class Notification(ABC):
    @abstractmethod
    def send(self, to, msg): ...

class EmailNotification(Notification):
    def send(self, to, msg): return f"email to {to}: {msg}"

class SmsNotification(Notification):
    def send(self, to, msg): return f"sms to {to}: {msg}"

class PushNotification(Notification):
    def send(self, to, msg): return f"push to {to}: {msg}"


class NotificationFactory:
    # A REGISTRY beats an if/elif chain: adding a channel is one dict entry,
    # and a plug-in can register itself without editing this file at all.
    _registry = {
        "email": EmailNotification,
        "sms":   SmsNotification,
        "push":  PushNotification,
    }

    @classmethod
    def register(cls, name, klass):       # extension point for new channels
        cls._registry[name] = klass

    @classmethod
    def create(cls, channel) -> Notification:
        try:
            return cls._registry[channel]()      # look up, then construct
        except KeyError:
            # Fail loudly with the valid options - a config typo should not
            # silently send nothing.
            raise ValueError(f"unknown channel {channel!r}; "
                             f"expected one of {sorted(cls._registry)}")

# The caller never imports EmailNotification and never sees the branching.
NotificationFactory.create("sms").send("+353...", "Your order shipped")
'''),
          example="`json.loads` returning dict / list / int / str depending on the text is a factory: you ask for a Python object and it decides the concrete type. So is a database driver's connect(url) picking a Postgres or MySQL connection class from the scheme.",
          pitfalls="A god-factory that builds unrelated things; hiding real construction errors behind a silent None return; adding a factory when there is exactly one implementation and no plans for a second.",
          followups="'Factory vs Builder?' Factory chooses WHICH class; Builder assembles ONE complicated object step by step. 'How would you add a channel without editing the factory?' Registration - each channel module calls NotificationFactory.register(...) at import, which is how plug-in systems work."),

        Q("lld", "Pattern: Singleton - and why interviewers are suspicious of it",
          "Singleton guarantees exactly one instance of a class exists and gives everyone a global way to reach it. Legitimate uses are narrow: a connection pool, a logger, an in-memory config loaded once at boot, a metrics registry - things where a second copy would be actively wrong or wasteful. Know it because it is asked constantly, but know the criticism too, because the strongest answer names both. The problems: it is a global variable in a costume, so any class can reach it without declaring the dependency, which makes call graphs invisible; it wrecks unit tests, since state set by test A leaks into test B and there is no seam to inject a fake; and it needs care to make thread-safe (two threads can both pass the `if _instance is None` check - the classic fix is double-checked locking, or in Python simply defining it at module level, because module import is already atomic and cached). The mature position to state in an interview: 'I'd use a single INSTANCE, but I'd create it once at start-up and inject it, rather than have every class fetch a global. Same one-copy guarantee, still testable.'",
          ["singleton", "pattern", "design-patterns", "lld", "oop", "creational"],
          difficulty="Easy",
          frequency="Very commonly asked - often as a trap to see whether you know its downsides.",
          mnemonic="Singleton = a global variable wearing a class costume. Use one INSTANCE, but INJECT it. The thread-safety trap is two threads passing the same `is None` check.",
          code=_c('''
import threading

# The interview answer: thread-safe, lazily created, double-checked.
class ConnectionPool:
    _instance = None
    _lock = threading.Lock()          # class-level: shared by all callers

    def __new__(cls, *a, **kw):
        if cls._instance is None:               # 1st check: cheap, no lock,
            with cls._lock:                     #    skipped by 99.99% of calls
                if cls._instance is None:       # 2nd check: the real one, under
                    inst = super().__new__(cls) #    the lock, so only one wins
                    inst._init_pool()
                    cls._instance = inst
        return cls._instance

    def _init_pool(self):
        self.connections = []          # expensive setup runs exactly once

# Without the SECOND check, two threads that both passed the first check would
# both construct a pool and one would be silently discarded (leaking sockets).

# The Pythonic version - a module-level object. Python caches modules on first
# import, so this is already a thread-safe singleton with no ceremony:
#     # pool.py
#     pool = ConnectionPool()
#     # anywhere else:  from pool import pool

# The version an interviewer prefers to hear: one instance, but INJECTED, so a
# test can hand in a fake and nothing reaches for a global.
class OrderService:
    def __init__(self, pool):          # dependency is visible in the signature
        self.pool = pool
'''),
          example="A logger is the standard honest singleton: you want one file handle, one buffer and one flush policy, and a second logger writing to the same file interleaves lines badly.",
          pitfalls="Forgetting thread-safety and doing the naive `if _instance is None` (the top follow-up); using a singleton for mutable application state, which makes tests order-dependent and flaky; assuming one-per-process is one-per-cluster - with three servers you have three singletons.",
          followups="'Why do people call it an anti-pattern?' Hidden dependencies plus untestability. 'How do you get one instance without a Singleton?' Construct it once in your composition root at start-up and pass it down - dependency injection gives you the same guarantee with none of the coupling."),

        Q("lld", "Pattern: Observer - publish/subscribe inside one process",
          "In plain words: one object (the subject) keeps a list of interested parties (observers) and calls them all when something happens. It exists so the source of an event does not have to know who cares. Without it, placing an order means OrderService directly calling EmailService, then InventoryService, then AnalyticsService, then LoyaltyService - and every new reaction edits OrderService, which is an Open/Closed violation and a merge-conflict magnet. With Observer, OrderService publishes 'order_placed' and each listener subscribes itself; adding a reaction touches only the new file. The give-away words in a prompt are 'notify', 'when X happens, also do Y and Z', 'subscribe', 'react to'. Two details worth mentioning unprompted: this is SYNCHRONOUS by default, so a slow observer slows the publisher and a throwing observer can break the whole publish - wrap each callback in try/except and consider handing off to a queue; and holding observer references forever is a memory leak in long-lived apps, so provide unsubscribe. Scaling the same idea across machines gives you a message broker like Kafka or SNS/SQS.",
          ["observer", "pattern", "design-patterns", "pubsub", "lld", "oop", "behavioral-pattern"],
          difficulty="Medium",
          frequency="Commonly asked - shows up in notification, stock-ticker, chat and any 'when X happens then...' design.",
          mnemonic="Observer = a mailing list. The publisher shouts once, everyone subscribed hears it, and nobody in the room knows who else is on the list.",
          code=_c('''
from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod
    def update(self, event, payload): ...

class Subject:
    def __init__(self):
        self._observers = []                 # who wants to know

    def subscribe(self, obs):   self._observers.append(obs)
    def unsubscribe(self, obs): self._observers.remove(obs)   # avoid the leak

    def notify(self, event, payload):
        for obs in list(self._observers):    # copy: an observer may unsubscribe
            try:
                obs.update(event, payload)
            except Exception as e:
                # One broken listener must NOT stop the others or the publisher.
                print(f"observer {obs} failed: {e}")

class OrderService(Subject):
    def place(self, order):
        # ... save the order ...
        self.notify("order_placed", order)   # we do NOT know who reacts

class EmailListener(Observer):
    def update(self, event, order): print(f"confirmation email for {order['id']}")

class InventoryListener(Observer):
    def update(self, event, order): print(f"decrement stock for {order['sku']}")

svc = OrderService()
svc.subscribe(EmailListener())
svc.subscribe(InventoryListener())     # a THIRD reaction = a new class + one line
svc.place({"id": 1, "sku": "abc"})
'''),
          example="A spreadsheet is the everyday Observer: the chart and the total cell subscribe to the data range, so editing one number updates both without the cell knowing what a chart is.",
          pitfalls="Silent failure - swallowing observer exceptions with a bare except and never logging; notification storms where observer A's update triggers another notify and you loop forever; forgetting unsubscribe, so a long-running server keeps dead objects alive.",
          followups="'What if an observer is slow?' Push the event onto a queue and let workers consume it - that is the same pattern, made asynchronous. 'How does this differ from a message broker?' Only in scope: Observer is in-process and loses events on crash, a broker persists them and crosses machines."),

        Q("lld", "Pattern: Builder - constructing an object with many optional parts",
          "The problem it solves is the telescoping constructor: Pizza(size), Pizza(size, cheese), Pizza(size, cheese, olives), Pizza(size, cheese, olives, extra_sauce, thin_crust)... Callers end up writing `Pizza(12, True, False, False, True)` and nobody can read it, a swapped pair of booleans compiles fine and is wrong, and every new option multiplies the overloads. Builder replaces that with named, chainable steps and one build() at the end that validates and returns an immutable object. Use it when there are many optional parameters, when some combinations are invalid and need checking in one place, or when you want the finished object to be read-only. Python softens the need because keyword arguments and defaults already give you `Pizza(size=12, cheese=True)` - so the honest interview answer is 'in Python I'd start with keyword args plus a dataclass, and reach for a real Builder when construction has multi-step validation or the object must be immutable'. Saying that, rather than reciting the Java version, shows judgement.",
          ["builder", "pattern", "design-patterns", "lld", "oop", "creational"],
          difficulty="Easy",
          frequency="Commonly asked, especially as 'how would you construct this object cleanly?' inside a larger design.",
          mnemonic="Builder = ordering at a counter: 'large, extra cheese, no olives' then 'that's my order'. Named steps, then one build() that checks it makes sense.",
          code=_c('''
class Pizza:
    """Finished product - built once, then read-only."""
    def __init__(self, size, toppings, crust):
        self.size, self.toppings, self.crust = size, tuple(toppings), crust
    def __repr__(self):
        return f"Pizza({self.size}in {self.crust}, {list(self.toppings)})"

class PizzaBuilder:
    def __init__(self):
        self._size, self._crust, self._toppings = 12, "regular", []

    # Each step returns self, which is what lets you CHAIN the calls.
    def size(self, inches):    self._size = inches;        return self
    def crust(self, kind):     self._crust = kind;         return self
    def add(self, topping):    self._toppings.append(topping); return self

    def build(self):
        # ONE place for cross-field validation - impossible with plain setters.
        if self._size > 16 and self._crust == "thin":
            raise ValueError("thin crust is not available above 16 inches")
        if len(self._toppings) > 8:
            raise ValueError("max 8 toppings")
        return Pizza(self._size, self._toppings, self._crust)

pizza = (PizzaBuilder()
         .size(14)
         .crust("thin")
         .add("cheese")
         .add("mushroom")
         .build())          # <- reads like a sentence, and validates once

# Compare: Pizza(14, True, False, True, False, "thin") - which flag is olives?
'''),
          example="Real ones you have used: a SQL query builder (`session.query(User).filter(...).order_by(...).limit(10)`), and HTTP request builders. Both chain named steps and only execute at the terminal call.",
          pitfalls="Letting build() be called twice on the same builder and sharing the mutable topping list between products (copy it, as above with tuple()); no validation in build(), which throws away the pattern's main benefit; using a Builder for a two-field object.",
          followups="'What is the Pythonic alternative?' A frozen dataclass with keyword defaults, plus a __post_init__ for validation. 'How does Builder differ from Factory?' Factory picks WHICH class to make in one call; Builder makes ONE class in several configured steps."),

        Q("lld", "Pattern: Decorator - add behaviour without touching the class",
          "In plain words: wrap an object in another object that has the SAME interface, does a little extra, and passes the call through. The caller cannot tell the difference, so you can stack wrappers freely: a plain coffee wrapped in milk wrapped in sugar is still something you can call cost() on. It exists to defeat the subclass explosion - with 3 sizes and 5 add-ons, inheritance needs a class per combination, while Decorator needs 3 + 5 pieces and supports every combination, including ones nobody enumerated. The structural requirement is that the wrapper implements the same interface as the thing it wraps and holds a reference to it. Recognise it in a prompt by 'optional add-ons', 'in any combination', or a price/behaviour that accumulates. You have used it already: Python's `@lru_cache` and `@login_required` are decorators, and file streams are the canonical example (a buffered stream wrapping a compressed stream wrapping a raw file - each adds one concern and none knows about the others).",
          ["decorator", "pattern", "design-patterns", "lld", "oop", "structural"],
          difficulty="Medium",
          frequency="Commonly asked - and doubly relevant in Python, where the syntax is built in.",
          mnemonic="Decorator = Russian dolls with the same face. Each layer adds one thing and forwards the rest, so any stack of layers still looks like the original object.",
          code=_c('''
from abc import ABC, abstractmethod

class Beverage(ABC):
    @abstractmethod
    def cost(self): ...
    @abstractmethod
    def description(self): ...

class Espresso(Beverage):                 # the base object being wrapped
    def cost(self): return 2.00
    def description(self): return "espresso"

class AddOn(Beverage):
    """Same interface as Beverage, and HOLDS a Beverage. That is the trick."""
    def __init__(self, inner: Beverage):
        self.inner = inner

class Milk(AddOn):
    def cost(self):        return self.inner.cost() + 0.50   # add, then forward
    def description(self): return self.inner.description() + " + milk"

class Syrup(AddOn):
    def cost(self):        return self.inner.cost() + 0.30
    def description(self): return self.inner.description() + " + syrup"

drink = Syrup(Milk(Milk(Espresso())))     # double milk, one syrup
drink.cost()                              # 3.30
drink.description()                       # "espresso + milk + milk + syrup"
# Note double-milk works for free. Subclassing would need a DoubleMilkEspresso.

# Python has this as syntax - same idea, applied to functions:
import functools
def retry(times):
    def wrap(fn):
        @functools.wraps(fn)              # keeps the original name/docstring
        def inner(*a, **kw):
            for attempt in range(times):
                try:    return fn(*a, **kw)
                except Exception:
                    if attempt == times - 1: raise
        return inner
    return wrap

@retry(3)                                 # fetch() is now wrapped in retry logic
def fetch(url): ...
'''),
          example="Streams: `GzipFile(BufferedWriter(open('f','wb')))`. Each layer adds compression or buffering, every layer still supports write(), and the caller does not care how deep the stack is.",
          pitfalls="Wrapping in the wrong order when order matters (compress-then-encrypt is not the same as encrypt-then-compress); deep stacks that make debugging a stack-trace maze; forgetting functools.wraps in Python, which silently renames every decorated function to 'inner'.",
          followups="'Decorator vs inheritance?' Decorator composes at runtime and combines freely; inheritance is fixed and multiplies classes. 'Decorator vs Proxy?' Same structure, different intent - Decorator ADDS behaviour, Proxy CONTROLS access (lazy loading, permissions, caching)."),

        Q("lld", "Pattern: Adapter - make an incompatible class fit your interface",
          "In plain words: a plug adapter. Your code expects a socket of one shape; the third-party library provides a different shape; the Adapter sits between them and translates. You use it when you cannot (or should not) change either side - a vendor SDK, a legacy module, a class from another team. The key benefit is that the incompatibility is confined to ONE small class instead of leaking into every caller: your business logic talks only to your own interface, so replacing the vendor later means writing a second adapter and changing one line of wiring. This is also how you keep an interview design testable - your PaymentProcessor interface is yours, StripeAdapter and PayPalAdapter implement it, and your tests inject a FakeAdapter. Recognise it in a prompt by 'we already have X, integrate it', 'support both providers', or any mention of a legacy or external system. Note the difference from Facade: Adapter changes an interface to match an expected one, while Facade invents a simpler interface over a complicated subsystem.",
          ["adapter", "pattern", "design-patterns", "lld", "oop", "structural", "integration"],
          difficulty="Easy",
          frequency="Commonly asked - the natural answer to 'how do you support a second vendor?'.",
          mnemonic="Adapter = a travel plug. Neither the laptop nor the wall changes; one small piece in the middle translates. All the ugliness lives in that one piece.",
          code=_c('''
from abc import ABC, abstractmethod

# 1. The interface OUR application wants to talk to. We own this.
class PaymentProcessor(ABC):
    @abstractmethod
    def pay(self, amount_eur: float, token: str) -> bool: ...

# 2. A third-party SDK we cannot modify. Different names, different units,
#    different return shape - all the usual sins.
class StripeSDK:
    def create_charge(self, amount_in_cents: int, currency: str, source: str):
        return {"status": "succeeded", "id": "ch_123"}

class PayPalSDK:
    def make_payment(self, value: str, cc: str):     # amount as a STRING
        return True

# 3. One adapter per vendor. Every translation lives here and nowhere else.
class StripeAdapter(PaymentProcessor):
    def __init__(self, sdk: StripeSDK): self.sdk = sdk
    def pay(self, amount_eur, token):
        cents = int(round(amount_eur * 100))         # unit conversion
        result = self.sdk.create_charge(cents, "eur", token)
        return result["status"] == "succeeded"       # shape conversion

class PayPalAdapter(PaymentProcessor):
    def __init__(self, sdk: PayPalSDK): self.sdk = sdk
    def pay(self, amount_eur, token):
        return bool(self.sdk.make_payment(f"{amount_eur:.2f}", token))

# 4. Business logic depends on the ABSTRACTION and never sees a vendor name.
class Checkout:
    def __init__(self, processor: PaymentProcessor): self.processor = processor
    def confirm(self, order):
        return self.processor.pay(order["total"], order["token"])

Checkout(StripeAdapter(StripeSDK())).confirm({"total": 42.5, "token": "tok"})
'''),
          example="Python's `io.TextIOWrapper` adapts a byte stream to a text interface. Every ORM is a large adapter: your objects on one side, SQL rows on the other.",
          pitfalls="Letting vendor types escape through the adapter (returning a StripeCharge object means the vendor has leaked into your code after all); adapters that quietly swallow vendor-specific errors instead of mapping them to your own exception types; one giant adapter for three vendors instead of one each.",
          followups="'Adapter vs Facade?' Adapter matches an EXISTING expected interface; Facade invents a simpler one over a messy subsystem. 'How do you test it?' The adapter is the only piece needing a vendor sandbox or a recorded fixture - everything above it tests against a fake."),

        Q("lld", "Pattern: State - when an object's behaviour depends on its mode",
          "Some objects behave completely differently depending on what mode they are in: a vending machine ignores 'dispense' until money is inserted; an order can be cancelled while Pending but not once Shipped; a document can be edited in Draft but not in Published. Coding that with flags gives you methods full of `if self.status == 'pending' and not self.paid ...` repeated in every method, and the legal transitions exist only in the author's head. The State pattern makes each mode a class holding the behaviour AND the legal moves out of that mode: insert_coin() on IdleState returns HasMoneyState, while insert_coin() on DispensingState refuses. The context object just forwards every call to its current state and replaces that state with whatever comes back. The payoff is that illegal transitions become impossible rather than merely tested for, adding a mode is a new class, and the state machine is readable in one place. Recognise it by the words 'status', 'lifecycle', 'workflow', 'can only X when Y', or any prompt that hands you a list of statuses.",
          ["state", "pattern", "design-patterns", "state-machine", "lld", "oop"],
          difficulty="Medium",
          frequency="Commonly asked - the backbone of the vending machine, ATM, elevator and order-lifecycle LLD prompts.",
          mnemonic="State = each mode is a class that knows what it can do and which mode comes next. The object holds ONE state and forwards to it. No status flags, no if/elif in every method.",
          code=_c('''
from abc import ABC, abstractmethod

class OrderState(ABC):
    """Each state answers the same questions - differently."""
    @abstractmethod
    def pay(self, order): ...
    @abstractmethod
    def cancel(self, order): ...

class Pending(OrderState):
    def pay(self, order):    return Paid()          # returns the NEXT state
    def cancel(self, order): return Cancelled()

class Paid(OrderState):
    def pay(self, order):    raise ValueError("already paid")
    def cancel(self, order): return Refunding()     # cancelling now means a refund

class Shipped(OrderState):
    def pay(self, order):    raise ValueError("already paid")
    def cancel(self, order): raise ValueError("cannot cancel a shipped order")

class Cancelled(OrderState):
    def pay(self, order):    raise ValueError("order is cancelled")
    def cancel(self, order): return self            # cancelling twice is harmless

class Refunding(OrderState):
    def pay(self, order):    raise ValueError("refund in progress")
    def cancel(self, order): return self

class Order:
    def __init__(self):
        self.state = Pending()                      # the CONTEXT holds one state

    def pay(self):    self.state = self.state.pay(self)      # forward, then move
    def cancel(self): self.state = self.state.cancel(self)
    def status(self): return type(self.state).__name__

o = Order(); o.pay(); o.status()      # "Paid"
o.cancel(); o.status()                # "Refunding" - the rule lives in Paid, not
                                      # in a giant if/elif inside Order
'''),
          example="A traffic light: Red knows the next state is Green, Green knows it is Amber. No light needs a table of every other light's rules - each knows only its own successor.",
          pitfalls="Sprinkling state checks in the context anyway, which defeats the pattern; states holding data that belongs to the context (keep the DATA on the order and the BEHAVIOUR in the state); forgetting terminal states, so cancel-twice explodes instead of being a harmless no-op.",
          followups="'Draw the state diagram' - be ready to list every state and every legal edge, including the self-loops. 'State vs Strategy?' Identical structure, opposite intent: the client picks a Strategy and it rarely changes, while the object changes its own State as events arrive."),

        Q("lld", "Pattern: Command - turn an action into an object (and get undo free)",
          "In plain words: wrap 'do this thing' into an object with an execute() method, instead of calling the method directly. That sounds like extra ceremony until you notice what it buys: because the action is now a value, you can put it in a list (a queue of jobs), keep it in a history (undo/redo), retry it, log it, schedule it, or send it over a network. Add an undo() alongside execute() and the history stack IS your undo feature. The pieces are: a Command interface with execute/undo, concrete commands that hold the receiver plus the arguments they need, an Invoker that triggers commands without knowing what they do (a button, a job runner, a REPL), and the Receiver that does the real work. Recognise it in a prompt by 'undo', 'redo', 'job queue', 'macro', 'replay', 'audit log', or a remote control / menu where the same widget must be bound to different actions.",
          ["command", "pattern", "design-patterns", "undo", "lld", "oop"],
          difficulty="Medium",
          frequency="Commonly asked - the standard answer to text-editor undo, job queues, and remote-control style prompts.",
          mnemonic="Command = an action in a box. Once the action is an object you can queue it, log it, retry it, and reverse it. Undo is just a stack of boxes.",
          code=_c('''
from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self): ...
    @abstractmethod
    def undo(self): ...

class Document:                    # the RECEIVER - it does the real work
    def __init__(self): self.text = ""

class InsertText(Command):
    def __init__(self, doc, pos, s):
        self.doc, self.pos, self.s = doc, pos, s
    def execute(self):
        d = self.doc
        d.text = d.text[:self.pos] + self.s + d.text[self.pos:]
    def undo(self):                # the exact inverse of execute
        d = self.doc
        d.text = d.text[:self.pos] + d.text[self.pos + len(self.s):]

class DeleteRange(Command):
    def __init__(self, doc, start, end):
        self.doc, self.start, self.end, self.removed = doc, start, end, ""
    def execute(self):
        d = self.doc
        self.removed = d.text[self.start:self.end]   # REMEMBER, so undo can restore
        d.text = d.text[:self.start] + d.text[self.end:]
    def undo(self):
        d = self.doc
        d.text = d.text[:self.start] + self.removed + d.text[self.start:]

class Editor:                      # the INVOKER - knows nothing about the actions
    def __init__(self):
        self.done, self.undone = [], []
    def run(self, cmd):
        cmd.execute()
        self.done.append(cmd)
        self.undone.clear()        # a new action invalidates the redo branch
    def undo(self):
        if self.done:
            c = self.done.pop(); c.undo(); self.undone.append(c)
    def redo(self):
        if self.undone:
            c = self.undone.pop(); c.execute(); self.done.append(c)

doc, ed = Document(), Editor()
ed.run(InsertText(doc, 0, "hello world"))
ed.run(DeleteRange(doc, 0, 6)); doc.text      # "world"
ed.undo(); doc.text                            # "hello world"  <- free undo
'''),
          example="Every job queue is Command: a Celery/SQS task is a serialised 'do this with these arguments' object that some worker executes later, possibly on another machine.",
          pitfalls="Undo that recomputes instead of restoring (a delete must SAVE what it removed before removing it); forgetting to clear the redo stack after a new action, which lets redo replay a branch that no longer exists; unbounded history, which leaks memory in a long editing session - cap it.",
          followups="'How would you support macros?' A CompositeCommand holding a list of commands, executing forward and undoing in REVERSE order. 'How does this scale to a distributed job queue?' Serialise the command (type plus arguments) to JSON, and make execute idempotent so a redelivered message is safe."),

        Q("lld", "Pattern: Repository / DAO - keep storage out of your business logic",
          "The idea: your domain classes should not know whether data lives in Postgres, DynamoDB, a JSON file or a dict in memory. A Repository is an interface with domain-shaped methods - save(order), find_by_id(id), find_pending_for(user) - and one implementation per storage technology. The business code depends on the interface. Three payoffs, and you should name all three. (1) TESTABILITY - an InMemoryOrderRepository is twenty lines and makes your service tests run in milliseconds with no database, which is the single biggest practical win. (2) SWAPPABILITY - moving from Postgres to DynamoDB is a new implementation, not a rewrite of every service. (3) VOCABULARY - `find_pending_for(user)` says what the business wants, whereas a raw SQL string scattered through a service says only how. The trap to avoid: a leaky repository whose methods take SQL fragments or return database rows - then the abstraction buys you nothing. Return domain objects and take domain arguments. This is also the honest answer when an interviewer asks 'where does persistence go in your parking-lot design?'.",
          ["repository", "dao", "pattern", "design-patterns", "persistence", "lld", "oop"],
          difficulty="Medium",
          frequency="Commonly asked as a follow-up to any LLD - 'now persist it' - and standard in backend interviews.",
          mnemonic="Repository = a collection you can query, that happens to be backed by a database. Domain words in, domain objects out - never SQL in the signature.",
          code=_c('''
from abc import ABC, abstractmethod

class Order:
    def __init__(self, id, user, total, status="pending"):
        self.id, self.user, self.total, self.status = id, user, total, status

class OrderRepository(ABC):
    """Domain vocabulary only - no SQL, no table names, no row objects."""
    @abstractmethod
    def save(self, order: Order) -> None: ...
    @abstractmethod
    def find_by_id(self, order_id) -> "Order | None": ...
    @abstractmethod
    def find_pending_for(self, user) -> list: ...

class InMemoryOrderRepository(OrderRepository):
    """The test double. Twenty lines, no database, runs in microseconds."""
    def __init__(self): self._rows = {}
    def save(self, order): self._rows[order.id] = order
    def find_by_id(self, order_id): return self._rows.get(order_id)
    def find_pending_for(self, user):
        return [o for o in self._rows.values()
                if o.user == user and o.status == "pending"]

class SqlOrderRepository(OrderRepository):
    """The real one. SQL is quarantined inside this file."""
    def __init__(self, conn): self.conn = conn
    def save(self, order):
        self.conn.execute(
            "INSERT INTO orders (id, user_id, total, status) VALUES (?,?,?,?) "
            "ON CONFLICT (id) DO UPDATE SET status = excluded.status",
            (order.id, order.user, order.total, order.status))
    def find_by_id(self, order_id):
        row = self.conn.execute(
            "SELECT id, user_id, total, status FROM orders WHERE id = ?",
            (order_id,)).fetchone()
        return Order(*row) if row else None          # rows -> domain objects
    def find_pending_for(self, user):
        rows = self.conn.execute(
            "SELECT id, user_id, total, status FROM orders "
            "WHERE user_id = ? AND status = 'pending'", (user,)).fetchall()
        return [Order(*r) for r in rows]

class CheckoutService:
    def __init__(self, repo: OrderRepository):       # injected -> testable
        self.repo = repo
    def cancel_all_pending(self, user):
        for o in self.repo.find_pending_for(user):
            o.status = "cancelled"
            self.repo.save(o)

# Unit test: CheckoutService(InMemoryOrderRepository()) - no database needed.
'''),
          example="Django's `Order.objects.filter(status='pending')` and SQLAlchemy sessions are repositories with the pattern already built in; you write your own when you want the domain vocabulary and the swappable seam explicitly.",
          pitfalls="find_all() then filtering in Python, which pulls the whole table over the network; a repository method per screen instead of per domain question, so it grows to fifty near-duplicates; letting ORM objects leak into the domain so a lazy-load fires deep inside business logic (the N+1 query problem).",
          followups="'Where do transactions live?' Above the repository - a Unit of Work or service method that commits once, so two saves either both land or neither does. 'Isn't this just the DAO pattern?' Near enough for an interview: DAO is table-shaped, Repository is domain-shaped, and both exist to keep SQL out of your business code."),
    ]

    # ── The classic LLD prompts, worked end to end ────────────────────────
    entries += [
        Q("lld", "LLD: Design a Parking Lot",
          "The most-asked OOD question at Amazon. CLARIFY FIRST (say these out loud): multiple floors? vehicle sizes? is pricing hourly or flat? one entrance or several? do we need to find the nearest spot, or any spot? Then commit to a scope - say 'multi-floor, three vehicle sizes, hourly pricing, any free spot of a fitting size'. NOUNS: ParkingLot, Floor, Spot, Vehicle, Ticket, Payment, PricingStrategy. VERBS: park, unpark, price, pay. THE KEY DECISIONS, each of which the interviewer is waiting for. (1) Spot sizing - a motorcycle can use a car spot but not vice versa, so model size as an ordered enum and allow a vehicle into any spot of equal or larger size; that one sentence handles the whole compatibility question. (2) Finding a spot fast - do NOT scan every spot on every entry; keep one free-spot collection per size (a set or heap per floor) so park() is O(1)-ish rather than O(total spots). (3) Pricing behind an interface, because it is the thing guaranteed to change (weekend rates, first hour free, EV surcharge). (4) The ticket is the receipt AND the timer: it carries the spot, the entry time, and later the exit time. (5) Concurrency - two cars must not get the same spot, so the free-list pop must be atomic; say this even before you are asked.",
          ["parking-lot", "lld", "ood", "amazon", "design", "strategy"],
          difficulty="Medium",
          frequency="Very commonly asked - the single most common Amazon SDE-1 OOD prompt.",
          mnemonic="Lot -> Floors -> Spots. Vehicle fits a spot of its size or bigger. Ticket = spot + entry time. Pricing behind an interface. Free spots in a PER-SIZE set so park() is not a linear scan.",
          code=_c('''
from enum import IntEnum
from abc import ABC, abstractmethod
import itertools, threading, datetime as dt

class Size(IntEnum):
    """IntEnum so we can COMPARE sizes: a bike fits in a car spot."""
    MOTORCYCLE = 1
    CAR = 2
    TRUCK = 3

class Vehicle:
    def __init__(self, plate, size: Size):
        self.plate, self.size = plate, size

class Spot:
    def __init__(self, spot_id, floor, size: Size):
        self.id, self.floor, self.size = spot_id, floor, size
        self.vehicle = None                  # association: the spot REFERENCES a car
    def fits(self, v: Vehicle):
        return self.vehicle is None and self.size >= v.size   # >= is the whole rule

class Ticket:
    _ids = itertools.count(1)
    def __init__(self, vehicle, spot):
        self.id = next(Ticket._ids)
        self.vehicle, self.spot = vehicle, spot
        self.entry = dt.datetime.now()
        self.exit = None

# --- pricing: the one thing certain to change, so it gets an interface ---
class PricingStrategy(ABC):
    @abstractmethod
    def amount(self, ticket) -> float: ...

class HourlyPricing(PricingStrategy):
    RATES = {Size.MOTORCYCLE: 1.0, Size.CAR: 2.5, Size.TRUCK: 4.0}
    def amount(self, ticket):
        hours = (ticket.exit - ticket.entry).total_seconds() / 3600
        billable = max(1, -(-hours // 1))            # ceil, minimum one hour
        return billable * self.RATES[ticket.vehicle.size]

class FreeFirstHour(PricingStrategy):                # added later, edits nothing
    def __init__(self, base): self.base = base
    def amount(self, ticket):
        hours = (ticket.exit - ticket.entry).total_seconds() / 3600
        return 0.0 if hours <= 1 else self.base.amount(ticket)

class ParkingLot:
    def __init__(self, spots, pricing: PricingStrategy):
        # Free spots bucketed BY SIZE: park() pops from a bucket instead of
        # scanning thousands of spots. This is the performance answer.
        self.free = {s: [] for s in Size}
        for sp in spots:
            self.free[sp.size].append(sp)
        self.occupied = {}                   # spot_id -> Ticket
        self.pricing = pricing
        self.lock = threading.Lock()         # two cars, one spot -> race

    def park(self, vehicle) -> Ticket:
        with self.lock:                      # check-and-take must be atomic
            # Try the exact size first, then progressively larger spots.
            for size in [s for s in Size if s >= vehicle.size]:
                if self.free[size]:
                    spot = self.free[size].pop()
                    spot.vehicle = vehicle
                    ticket = Ticket(vehicle, spot)
                    self.occupied[spot.id] = ticket
                    return ticket
            raise RuntimeError("lot full for this vehicle size")

    def unpark(self, ticket) -> float:
        with self.lock:
            if ticket.spot.id not in self.occupied:
                raise ValueError("ticket already used or invalid")   # double-exit
            ticket.exit = dt.datetime.now()
            fee = self.pricing.amount(ticket)
            spot = ticket.spot
            spot.vehicle = None
            self.free[spot.size].append(spot)      # return it to the pool
            del self.occupied[spot.id]
            return fee

spots = ([Spot(f"M{i}", 1, Size.MOTORCYCLE) for i in range(5)] +
         [Spot(f"C{i}", 1, Size.CAR) for i in range(20)] +
         [Spot(f"T{i}", 1, Size.TRUCK) for i in range(3)])
lot = ParkingLot(spots, FreeFirstHour(HourlyPricing()))
t = lot.park(Vehicle("221-D-1234", Size.CAR))
# ... later ...  lot.unpark(t) -> fee
'''),
          example="A motorcycle arrives when all bike spots are taken but car spots are free: the `for size in [s for s in Size if s >= vehicle.size]` loop falls through to CAR and parks it there. A truck in the same situation correctly fails, because nothing is bigger than TRUCK.",
          pitfalls="Scanning every spot on every entry (fine for 50 spots, hopeless for 5,000 - and the interviewer will ask); forgetting that a bigger spot can hold a smaller vehicle; no lock, so two cars get the same spot; no guard against reusing a ticket; putting the fee arithmetic inside ParkingLot so the first pricing change edits the core class.",
          followups="'Support electric charging spots' - EV becomes a spot ATTRIBUTE plus a filter, not a subclass, because a car may or may not need charging. 'Find the nearest spot to the entrance' - store spots in a per-size min-heap keyed by distance instead of a list; park() stays O(log n). 'Multiple entrances at once' - the lock already covers it in-process; across servers, move the free list to Redis or use a conditional database UPDATE.",
          examples=[
              "Why the free-spot buckets matter, with numbers. A 5,000-spot airport lot with a linear scan does up to 5,000 checks per arrival, and at rush hour with two arrivals a second that is 10,000 checks a second of pure waste - and every one of them under the lock, so arrivals serialise. With per-size lists, park() is a single pop. The interviewer is not testing whether you can write a for-loop; they are testing whether you noticed the loop was the design.",
              "The size-compatibility rule in one comparison. Model Size as an IntEnum (MOTORCYCLE=1, CAR=2, TRUCK=3) and the entire compatibility matrix collapses to `spot.size >= vehicle.size`. Candidates who model sizes as strings end up writing a nested if/elif that is nine branches long and gets one wrong. Choosing a data representation that makes the rule trivial is a design decision worth narrating.",
              "The double-exit bug. A driver scans a ticket at the barrier, the barrier times out, they scan again. Without the `if ticket.spot.id not in self.occupied` guard, the second unpark pushes the same spot onto the free list twice - now two cars can be assigned to it and you have a physical collision in the real world. Interviewers love this because it is an idempotency question wearing a parking hat.",
              "Where pricing gets interesting. The follow-up is usually 'weekends are half price' or 'the first 15 minutes are free'. With HourlyPricing behind an interface, the answer is a new class - and FreeFirstHour above shows you can even WRAP an existing strategy (that is Decorator applied to Strategy) to compose rules. If pricing had been an if/elif inside unpark(), the same follow-up would have you editing the method that also manages the spot pool.",
              "Concurrency, said out loud before you are asked. Two cars arrive at two entrances in the same millisecond. Without the lock, both threads see the same last free spot in the CAR list and both pop... or worse, both read before either writes, and both drivers are directed to spot C7. One lock around find-and-take fixes it in-process. For several entrance servers, the honest answer is that the free list must live in one place - Redis with an atomic pop, or a database `UPDATE spots SET ticket_id = ? WHERE id = ? AND ticket_id IS NULL` that returns a row count.",
              "Scope control wins points. If you start by drawing Vehicle, Car, Truck, Motorcycle, Bus, ElectricCar, Floor, Spot, Entrance, Exit, Gate, Barrier, Camera, Ticket, Payment, CreditCardPayment, CashPayment, Receipt, Admin and Report, you will run out of time with nothing working. Say instead: 'three sizes, one pricing rule, any fitting spot; I'll write ParkingLot, Spot and the pricing properly and describe the rest'. Then write real code. Finished-and-narrow beats sketched-and-broad every time.",
          ]),

        Q("lld", "LLD: Design an Elevator system",
          "This one is really 'can you design a scheduler?'. CLARIFY: how many lifts and floors, do we handle just one lift or a bank of them, are there express or service lifts, do we need to model door timing? Commit to: N lifts, M floors, external (hall) and internal (cabin) requests, a pluggable dispatch algorithm. THE CORE INSIGHT is that there are two request types with different meanings - an EXTERNAL request is (floor, direction) and can be served by ANY lift, whereas an INTERNAL request is (lift, floor) and belongs to one specific cabin. Every good design keeps them separate. THE SECOND INSIGHT is the classic elevator algorithm (also known as SCAN, the same one used for disk-head scheduling): a lift keeps moving in its current direction, serving every stop on the way, and only reverses when there is nothing further ahead. This is why each lift holds two sorted structures - the stops above and the stops below - rather than a FIFO queue; a FIFO queue makes a lift bounce from floor 10 to floor 2 to floor 9 and is the most common wrong answer. The dispatcher (which lift takes a hall call?) is your extension point: nearest-idle is fine to start, then mention direction-aware scoring and load balancing as improvements.",
          ["elevator", "lld", "ood", "amazon", "scheduling", "state-machine", "design"],
          difficulty="Hard",
          frequency="Very commonly asked at Amazon; a favourite because scope is huge and how you cut it is the signal.",
          mnemonic="Two request types: hall calls (floor + direction, any lift) vs cabin calls (this lift, this floor). Each lift sweeps in one direction (SCAN) using an up-set and a down-set, never a FIFO queue. Dispatch policy = the pluggable part.",
          code=_c('''
from abc import ABC, abstractmethod
from enum import Enum
import heapq

class Direction(Enum):
    UP, DOWN, IDLE = 1, -1, 0

class Elevator:
    def __init__(self, eid, floor=0):
        self.id, self.floor = eid, floor
        self.direction = Direction.IDLE
        # SCAN needs stops split by side of the cabin, each kept sorted so we
        # always take the NEXT one in the current direction.
        self._up = []          # min-heap of floors above us
        self._down = []        # max-heap (negated) of floors below us

    def request_stop(self, floor):
        """A cabin (internal) request, or a hall call assigned to this lift."""
        if floor > self.floor:  heapq.heappush(self._up, floor)
        elif floor < self.floor: heapq.heappush(self._down, -floor)
        # floor == self.floor: we are already here, just open the doors

    def next_stop(self):
        if self.direction == Direction.UP and self._up:   return self._up[0]
        if self.direction == Direction.DOWN and self._down: return -self._down[0]
        if self._up:   return self._up[0]          # nothing ahead -> reverse
        if self._down: return -self._down[0]
        return None                                 # idle

    def step(self):
        """One tick of simulated time: move one floor toward the next stop."""
        target = self.next_stop()
        if target is None:
            self.direction = Direction.IDLE
            return
        self.direction = Direction.UP if target > self.floor else Direction.DOWN
        self.floor += self.direction.value
        if self.floor == target:                    # arrived - pop and open
            if self.direction == Direction.UP: heapq.heappop(self._up)
            else:                              heapq.heappop(self._down)

    def pending(self):
        return len(self._up) + len(self._down)


class DispatchStrategy(ABC):
    """WHICH lift answers a hall call - the piece most likely to change."""
    @abstractmethod
    def pick(self, elevators, floor, direction): ...

class NearestIdleFirst(DispatchStrategy):
    def pick(self, elevators, floor, direction):
        idle = [e for e in elevators if e.direction == Direction.IDLE]
        pool = idle or elevators
        return min(pool, key=lambda e: abs(e.floor - floor))

class DirectionAware(DispatchStrategy):
    """Prefer a lift already heading your way and about to pass your floor -
    it costs it nothing extra, which is the whole point of the real algorithm."""
    def pick(self, elevators, floor, direction):
        def score(e):
            gap = abs(e.floor - floor)
            heading_here = (e.direction == direction and
                            ((direction == Direction.UP and e.floor <= floor) or
                             (direction == Direction.DOWN and e.floor >= floor)))
            if heading_here:                 return gap            # best
            if e.direction == Direction.IDLE: return gap + 5       # decent
            return gap + 15 + e.pending()    # busy and going the wrong way
        return min(elevators, key=score)

class ElevatorSystem:
    def __init__(self, n, strategy: DispatchStrategy):
        self.elevators = [Elevator(i) for i in range(n)]
        self.strategy = strategy

    def hall_call(self, floor, direction):        # EXTERNAL request
        lift = self.strategy.pick(self.elevators, floor, direction)
        lift.request_stop(floor)
        return lift.id

    def cabin_call(self, lift_id, floor):         # INTERNAL request
        self.elevators[lift_id].request_stop(floor)

    def tick(self):
        for e in self.elevators: e.step()
'''),
          example="Lift at floor 3 heading up with stops at 5 and 9. A hall call comes from floor 7 going up. DirectionAware gives it to this lift because it will pass 7 anyway, and the stop set becomes {5, 7, 9} - one extra door-open, no detour. A FIFO queue would have served 5, then 9, then come back down to 7.",
          pitfalls="A single FIFO queue of floors, which makes the lift yo-yo; treating hall calls and cabin calls as the same thing (a hall call at floor 7 'going down' must not be answered by a lift that will arrive going up); no strategy seam, so 'now optimise for wait time' means rewriting the core; ignoring capacity and door state entirely when asked to model a real building.",
          followups="'How do you measure whether your dispatcher is good?' Average wait time and worst-case wait, simulated over a rush-hour arrival pattern - and note the tension: greedy nearest-lift minimises the mean but starves the top floors. 'How would you handle morning rush?' Zoning or parking idle lifts at the lobby, a real technique called up-peak mode."),

        Q("lld", "LLD: Design a Vending Machine (the state-machine question)",
          "This prompt exists to see whether you reach for the State pattern. CLARIFY: coins only or cards too, do we give change, what happens when the item is sold out, can the user cancel mid-transaction? Commit to: coins, change given, cancel supported, sold-out handled. The naive design is a Machine class with `self.status = 'idle'` and every method starting with a stack of status checks; it works for three states and rots immediately. THE STATE DESIGN gives each mode a class - Idle (accepts a product selection), HasMoney (accepts more coins, dispenses when paid, refunds on cancel), Dispensing (rejects everything until finished), SoldOut (refuses selection). Each state returns the next state, so the legal transitions are visible in one place and an illegal one is impossible rather than merely guarded. THE OTHER THING BEING TESTED is change-making: keep a coin inventory, and give change greedily from the largest denomination down - but say out loud that greedy is only optimal for canonical coin systems, and that if you cannot make exact change you must refuse the sale and refund rather than short-change the customer. That single sentence is the difference between a passing and a strong answer.",
          ["vending-machine", "lld", "ood", "state-machine", "state", "amazon", "design"],
          difficulty="Medium",
          frequency="Very commonly asked - the standard prompt for testing the State pattern.",
          mnemonic="Idle -> HasMoney -> Dispensing -> Idle, with Cancel returning to Idle plus a refund and SoldOut as a dead end. Each state is a class that returns the NEXT state. Greedy change from the largest coin, and refuse the sale if exact change is impossible.",
          code=_c('''
from abc import ABC, abstractmethod

COINS = [200, 100, 50, 20, 10]                # cents, largest first

class Product:
    def __init__(self, code, name, price_cents, qty):
        self.code, self.name, self.price, self.qty = code, name, price_cents, qty

class State(ABC):
    @abstractmethod
    def select(self, m, code): ...
    @abstractmethod
    def insert(self, m, coin): ...
    @abstractmethod
    def cancel(self, m): ...

class Idle(State):
    def select(self, m, code):
        p = m.products.get(code)
        if not p or p.qty == 0:
            raise ValueError("sold out")            # stay in Idle
        m.selected = p
        return HasMoney()                            # -> next state
    def insert(self, m, coin):
        raise ValueError("select a product first")
    def cancel(self, m):
        return self                                  # nothing to cancel

class HasMoney(State):
    def select(self, m, code):
        raise ValueError("finish or cancel the current purchase first")
    def insert(self, m, coin):
        if coin not in COINS: raise ValueError("coin rejected")
        m.inserted += coin
        if m.inserted < m.selected.price:
            return self                              # keep collecting
        change = m.inserted - m.selected.price
        coins = m.plan_change(change)                # can we even pay it back?
        if coins is None:
            m.refund()                               # honesty beats a sale
            raise ValueError("cannot give exact change - refunded")
        return Dispensing(coins)
    def cancel(self, m):
        m.refund()
        return Idle()

class Dispensing(State):
    def __init__(self, change_coins): self.change_coins = change_coins
    def select(self, m, code):  raise ValueError("busy dispensing")
    def insert(self, m, coin):  raise ValueError("busy dispensing")
    def cancel(self, m):        raise ValueError("too late to cancel")
    def finish(self, m):
        m.selected.qty -= 1
        for c in self.change_coins:
            m.bank[c] -= 1                           # pay the change out
        m.inserted, m.selected = 0, None
        return Idle()

class VendingMachine:
    def __init__(self, products, bank):
        self.products = {p.code: p for p in products}
        self.bank = dict(bank)                # coin value -> how many we hold
        self.state, self.inserted, self.selected = Idle(), 0, None

    # The machine just FORWARDS to the current state and stores what comes back.
    def select(self, code): self.state = self.state.select(self, code)
    def insert(self, coin):
        self.bank[coin] = self.bank.get(coin, 0) + 1
        self.state = self.state.insert(self, coin)
        if isinstance(self.state, Dispensing):
            self.state = self.state.finish(self)
    def cancel(self): self.state = self.state.cancel(self)

    def plan_change(self, amount):
        """Greedy, largest coin first, and honest about failure."""
        plan, held = [], dict(self.bank)
        for c in COINS:
            while amount >= c and held.get(c, 0) > 0:
                plan.append(c); held[c] -= 1; amount -= c
        return plan if amount == 0 else None      # None = refuse the sale

    def refund(self):
        self.inserted, self.selected = 0, None
'''),
          example="Item costs 150c, the user inserts 200c, and the machine holds no 50c coins. plan_change(50) returns None, so instead of shorting the customer the machine refunds the 200c and says it cannot give change - which is exactly what a real machine does.",
          pitfalls="Status flags plus if/elif in every method instead of state classes; allowing selection while dispensing; taking the money before checking that change is possible; assuming greedy change always works (it does not for made-up coin sets like {1, 3, 4} where 6 needs 3+3, not 4+1+1) - say this even though real currencies are canonical.",
          followups="'Add card payment' - a PaymentMethod interface, with the state machine unchanged because HasMoney only cares 'is the balance covered'. 'Make it thread-safe' - one machine, one physical user, so a single lock around the whole transaction is genuinely the right answer here; say so rather than over-engineering."),

        Q("lld", "LLD: Design a Library Management system",
          "A gentler prompt that tests whether you can separate the THING from the COPY - the single distinction the whole design turns on. A Book (title, author, ISBN) is a catalogue record; a BookCopy (barcode, shelf, condition) is a physical object you can actually lend. Candidates who model one class find themselves unable to say 'we have four copies of this, two out on loan'. NOUNS: Book, BookCopy, Member, Loan, Reservation, Catalogue, Fine. VERBS: search, borrow, return, reserve, computeFine. THE DECISIONS: (1) A Loan links one COPY to one member with a due date - never a Book to a member. (2) Borrowing limits and fine rules are policy, so put them behind a small interface, because 'students get 5 books for 14 days but staff get 20 for 90 days' is the guaranteed follow-up. (3) Search needs an index (a dict from author and from title to book ids), not a linear scan of the catalogue. (4) A returned copy should immediately be offered to the first person in that book's reservation queue - a plain FIFO deque - which is the piece most candidates forget until prompted.",
          ["library", "lld", "ood", "design", "amazon"],
          difficulty="Easy",
          frequency="Commonly asked as a warm-up OOD, and very common in campus interviews.",
          mnemonic="Book = the title; BookCopy = the physical object with a barcode. You lend COPIES, not books. Loan = copy + member + due date. Policy (limits, fines) behind an interface. Reservation queue is a FIFO the return path drains.",
          code=_c('''
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import datetime as dt, itertools

class Book:
    """The CATALOGUE record - one per title."""
    def __init__(self, isbn, title, author):
        self.isbn, self.title, self.author = isbn, title, author

class BookCopy:
    """A PHYSICAL object on a shelf - many per Book."""
    def __init__(self, barcode, isbn):
        self.barcode, self.isbn, self.on_loan = barcode, isbn, False

class Member:
    def __init__(self, mid, name, kind="student"):
        self.id, self.name, self.kind = mid, name, kind

class Loan:
    _ids = itertools.count(1)
    def __init__(self, copy, member, days):
        self.id = next(Loan._ids)
        self.copy, self.member = copy, member
        self.out = dt.date.today()
        self.due = self.out + dt.timedelta(days=days)
        self.returned = None

class LendingPolicy(ABC):
    """'Students get 5 for 14 days, staff 20 for 90' is the sure follow-up."""
    @abstractmethod
    def max_loans(self, member): ...
    @abstractmethod
    def loan_days(self, member): ...
    @abstractmethod
    def fine(self, loan, on): ...

class StandardPolicy(LendingPolicy):
    LIMITS = {"student": (5, 14), "staff": (20, 90)}
    def max_loans(self, m): return self.LIMITS[m.kind][0]
    def loan_days(self, m): return self.LIMITS[m.kind][1]
    def fine(self, loan, on):
        late = (on - loan.due).days
        return max(0, late) * 0.20              # 20c a day, no fine if on time

class Library:
    def __init__(self, policy: LendingPolicy):
        self.policy = policy
        self.books, self.copies = {}, {}                  # isbn->Book, barcode->Copy
        self.by_isbn = defaultdict(list)                  # isbn -> [BookCopy]
        self.by_author = defaultdict(set)                 # SEARCH INDEX, not a scan
        self.by_title_word = defaultdict(set)
        self.loans_of = defaultdict(list)                 # member id -> [Loan]
        self.reservations = defaultdict(deque)            # isbn -> FIFO of members

    def add_copy(self, book: Book, barcode):
        self.books.setdefault(book.isbn, book)
        copy = BookCopy(barcode, book.isbn)
        self.copies[barcode] = copy
        self.by_isbn[book.isbn].append(copy)
        self.by_author[book.author.lower()].add(book.isbn)
        for w in book.title.lower().split():
            self.by_title_word[w].add(book.isbn)          # cheap inverted index

    def search(self, term):
        term = term.lower()
        ids = self.by_author.get(term, set()) | self.by_title_word.get(term, set())
        return [self.books[i] for i in ids]

    def available(self, isbn):
        return [c for c in self.by_isbn[isbn] if not c.on_loan]

    def borrow(self, member, isbn):
        active = [l for l in self.loans_of[member.id] if l.returned is None]
        if len(active) >= self.policy.max_loans(member):
            raise ValueError("loan limit reached")
        # Respect the queue: if someone reserved this and it is not you, wait.
        q = self.reservations[isbn]
        if q and q[0].id != member.id:
            raise ValueError("reserved by another member")
        free = self.available(isbn)
        if not free:
            self.reservations[isbn].append(member)        # auto-queue instead
            raise ValueError("no copies free - you are in the queue")
        if q and q[0].id == member.id: q.popleft()
        copy = free[0]; copy.on_loan = True
        loan = Loan(copy, member, self.policy.loan_days(member))
        self.loans_of[member.id].append(loan)
        return loan

    def return_copy(self, loan, on=None):
        on = on or dt.date.today()
        loan.returned = on
        loan.copy.on_loan = False
        fine = self.policy.fine(loan, on)
        q = self.reservations[loan.copy.isbn]
        notify = q[0] if q else None          # the piece candidates forget
        return fine, notify
'''),
          example="Four copies of one ISBN, three on loan. A member borrows the fourth; the next requester is appended to the reservation deque; when any copy comes back, return_copy hands the front of that queue back to the caller to notify.",
          pitfalls="Modelling only Book, so multiple copies are impossible; a linear scan over every book for search; hard-coded limits and fine rates inside Library; letting a member borrow a copy that a queued member has been waiting for; never marking the loan returned, so fines accrue forever.",
          followups="'How would you support renewals?' Extend the due date only if nobody has reserved that ISBN - the reservation queue is already the arbiter. 'How would search scale to a million titles?' The inverted index above is the right shape; move it to a real search engine when you need ranking, typo tolerance and phrase queries."),

        Q("lld", "LLD: Design an ATM",
          "Two things are being tested: a clean state machine, and cash dispensing - which is a small algorithm with a real trap. CLARIFY: card and PIN, multiple accounts per card, which denominations, do we allow deposits? Commit to: card plus PIN, withdrawal and balance enquiry, notes of 50/20/10. STATE MACHINE: Idle -> CardInserted -> Authenticated -> TransactionSelected -> Dispensing -> Idle, with a PIN retry counter that eats the card after three failures. THE DISPENSE ALGORITHM: greedy from the largest note works for real currency sets, but you must check FEASIBILITY BEFORE debiting - plan the notes, and if you cannot make the exact amount from the notes you actually hold, refuse the whole transaction. THE ORDER OF OPERATIONS IS THE ACTUAL TEST: check balance, plan the notes, debit the account, then dispense - and be able to say what happens if the dispenser jams after the debit. The honest answer is that the two actions must be reconciled: log the intent, and either the machine confirms the dispense or a compensating credit is issued. An interviewer asking 'what if the power cuts mid-withdrawal?' is asking about atomicity, not about ATMs.",
          ["atm", "lld", "ood", "state-machine", "design", "transactions"],
          difficulty="Medium",
          frequency="Commonly asked - a favourite because the failure cases are genuinely interesting.",
          mnemonic="Idle -> CardInserted -> Authenticated -> Dispensing. Plan the notes BEFORE you debit, refuse if you cannot pay exactly, and know your answer for 'the machine jammed after the debit' (log intent, then reconcile or compensate).",
          code=_c('''
from enum import Enum, auto

NOTES = [50, 20, 10]                     # largest first

class ATMState(Enum):
    IDLE = auto(); CARD_INSERTED = auto(); AUTHENTICATED = auto(); DISPENSING = auto()

class Account:
    def __init__(self, number, balance): self.number, self.balance = number, balance

class Card:
    def __init__(self, number, pin, account): self.number, self.pin, self.account = number, pin, account

class CashDispenser:
    def __init__(self, inventory):       # {50: 20, 20: 30, 10: 50}
        self.inventory = dict(inventory)

    def plan(self, amount):
        """Which notes would we hand out? None if we cannot pay EXACTLY."""
        plan, left = {}, amount
        for note in NOTES:
            take = min(left // note, self.inventory.get(note, 0))
            if take:
                plan[note] = take
                left -= take * note
        return plan if left == 0 else None

    def dispense(self, plan):
        for note, count in plan.items():
            self.inventory[note] -= count

class ATM:
    def __init__(self, dispenser, bank):
        self.state, self.card, self.tries = ATMState.IDLE, None, 0
        self.dispenser, self.bank = dispenser, bank
        self.journal = []                 # append-only log: survives a power cut

    def insert_card(self, card):
        if self.state != ATMState.IDLE: raise ValueError("busy")
        self.card, self.tries, self.state = card, 0, ATMState.CARD_INSERTED

    def enter_pin(self, pin):
        if self.state != ATMState.CARD_INSERTED: raise ValueError("no card")
        if pin != self.card.pin:
            self.tries += 1
            if self.tries >= 3:
                self.eject(retain=True)              # swallow the card
                raise ValueError("card retained after 3 failed attempts")
            raise ValueError(f"wrong PIN ({3 - self.tries} attempts left)")
        self.state = ATMState.AUTHENTICATED

    def withdraw(self, amount):
        if self.state != ATMState.AUTHENTICATED: raise ValueError("not authenticated")
        acct = self.card.account
        if amount <= 0 or amount % min(NOTES): raise ValueError("invalid amount")
        if amount > acct.balance:               raise ValueError("insufficient funds")
        plan = self.dispenser.plan(amount)      # FEASIBILITY BEFORE DEBIT
        if plan is None:
            raise ValueError("this machine cannot dispense that exact amount")
        self.state = ATMState.DISPENSING
        # Write the intent FIRST so a crash mid-dispense is reconcilable.
        self.journal.append(("withdraw", acct.number, amount, plan, "started"))
        acct.balance -= amount                  # debit
        self.dispenser.dispense(plan)           # then hand out the cash
        self.journal.append(("withdraw", acct.number, amount, plan, "done"))
        self.state = ATMState.AUTHENTICATED
        return plan

    def eject(self, retain=False):
        self.card, self.tries = None, 0
        self.state = ATMState.IDLE
'''),
          example="Balance 500, request 30, machine holds only 50s. plan(30) returns None, so the ATM refuses BEFORE debiting - the customer keeps their 500 and is told the machine cannot dispense that amount, which is what real ATMs do when they say 'try a multiple of 50'.",
          pitfalls="Debiting before checking the notes are available; using == on the exact amount without validating it is a multiple of the smallest note; no PIN attempt limit; no journal, so a crash between debit and dispense is unrecoverable; putting the note-planning arithmetic inside the ATM class instead of the dispenser.",
          followups="'The dispenser jams after the debit - what now?' The journal has a 'started' record with no 'done', so a reconciliation job re-credits the customer; this is exactly the compensating-transaction idea from distributed systems. 'Two ATMs, one account, simultaneous withdrawals' - the balance check and debit must be one atomic database operation (`UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?`), not a read followed by a write."),

        Q("lld", "LLD: Design Tic-Tac-Toe (and generalise it to N x N)",
          "Often given as a 30-minute warm-up, and the whole grade is in one detail: how you check for a win. The naive answer re-scans the entire board after every move, which is O(n^2) per move. The good answer keeps RUNNING COUNTS - one per row, one per column, and two for the diagonals - adding +1 for player X and -1 for player O; after a move you only touch the counters that move affects, and a counter reaching +n or -n means that player has won. That is O(1) per move and it generalises to any board size, which is exactly the follow-up ('now make it N x N', 'now make it Connect-4'). The rest is ordinary modelling: a Board that validates moves, a Player, a Game that alternates turns and detects a draw when the move count reaches n*n with no winner. Keep the win check on the Board (it owns the data), keep turn order in the Game, and do not let the two blur together.",
          ["tic-tac-toe", "game", "lld", "ood", "design", "amazon"],
          difficulty="Easy",
          frequency="Commonly asked as a warm-up OOD or a pair-programming exercise at both Amazon and Google.",
          mnemonic="Do not rescan the board. Keep row/col/diag counters, +1 for X and -1 for O; when any counter hits +n or -n that player has won. O(1) per move and it scales to N x N.",
          code=_c('''
class TicTacToe:
    """O(1) win detection via running counters - the point of the exercise."""
    def __init__(self, n=3):
        self.n = n
        self.rows = [0] * n            # +1 per X, -1 per O
        self.cols = [0] * n
        self.diag = 0                  # top-left to bottom-right
        self.anti = 0                  # top-right to bottom-left
        self.board = [[None] * n for _ in range(n)]
        self.moves = 0

    def move(self, r, c, player):      # player is +1 (X) or -1 (O)
        if not (0 <= r < self.n and 0 <= c < self.n):
            raise ValueError("off the board")
        if self.board[r][c] is not None:
            raise ValueError("square already taken")
        self.board[r][c] = player
        self.moves += 1

        # Only the lines through (r, c) can possibly change.
        self.rows[r] += player
        self.cols[c] += player
        if r == c:                 self.diag += player
        if r + c == self.n - 1:    self.anti += player

        target = player * self.n   # +n means X filled a line, -n means O did
        if (self.rows[r] == target or self.cols[c] == target or
                self.diag == target or self.anti == target):
            return "win"
        return "draw" if self.moves == self.n * self.n else "continue"


class Game:
    """Turn order and players live HERE; the board only knows about squares."""
    def __init__(self, n=3, names=("X", "O")):
        self.board = TicTacToe(n)
        self.names = names
        self.turn = 0                              # index into names

    def play(self, r, c):
        player = 1 if self.turn == 0 else -1
        result = self.board.move(r, c, player)
        if result == "win":  return f"{self.names[self.turn]} wins"
        if result == "draw": return "draw"
        self.turn ^= 1                             # alternate: 0 <-> 1
        return "next player"

g = Game()
g.play(0, 0); g.play(1, 1); g.play(0, 1); g.play(2, 2); g.play(0, 2)  # "X wins"
'''),
          example="On a 3x3 board X plays (0,0), (0,1), (0,2). rows[0] goes 1, 2, 3; the third move sees rows[0] == 3 == 1*n and reports a win, without ever looking at the other six squares.",
          pitfalls="Re-scanning eight lines after every move (works, but the follow-up 'make it 1000x1000' kills it); forgetting the anti-diagonal condition is r + c == n - 1; not detecting a draw; letting Game reach into board internals; using strings 'X' and 'O' as the cell value, which makes the counter trick impossible - the +1/-1 encoding is what buys you O(1).",
          followups="'Now Connect-4' - counters no longer suffice because you need runs of 4 anywhere, so scan the four directions outward from the last move only: O(k) per move, still not a full rescan. 'Add an unbeatable AI' - minimax with alpha-beta pruning; on 3x3 the whole game tree is about 250,000 nodes, small enough to search exhaustively."),

        Q("lld", "LLD: Design a Deck of Cards / Blackjack",
          "A short prompt that checks whether you separate DATA, RANDOMNESS and RULES. Three layers, and mixing them is the failure mode. (1) Card is an immutable value object - rank and suit, no behaviour beyond display. Making it immutable (a frozen dataclass) matters because cards get put in sets and dicts and copied between hands. (2) Deck owns the collection and the shuffle. Use Fisher-Yates - walk from the end, swap each position with a random earlier-or-equal one - because the tempting alternative of 'swap every card with a random card' is measurably biased and is a real interview gotcha; `random.shuffle` already does it correctly. (3) The RULES are game-specific and belong in a Game class, never in Card or Deck, because the same deck runs blackjack, poker and rummy. In blackjack the one interesting rule is the ace, worth 1 or 11: score the hand with all aces as 11, then downgrade one ace at a time while the total exceeds 21 - a three-line loop that candidates routinely get wrong by branching per ace.",
          ["cards", "blackjack", "game", "lld", "ood", "design", "shuffle"],
          difficulty="Easy",
          frequency="Commonly asked as a warm-up, and the Fisher-Yates detail comes up on its own.",
          mnemonic="Card = immutable value. Deck = collection + Fisher-Yates shuffle. Game = the rules. Aces: count them all as 11, then knock 10 off one at a time while you are bust.",
          code=_c('''
import random
from dataclasses import dataclass

RANKS = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]

@dataclass(frozen=True)          # frozen -> immutable and hashable
class Card:
    rank: str
    suit: str
    def __str__(self): return f"{self.rank} of {self.suit}"

class Deck:
    def __init__(self, packs=1):
        self.cards = [Card(r, s) for _ in range(packs) for s in SUITS for r in RANKS]
        self._dealt = 0

    def shuffle(self):
        # Fisher-Yates: for i from the end down, swap with a random j <= i.
        # Every permutation is equally likely. The naive "swap i with a random
        # index anywhere" is BIASED - a classic interview trap.
        for i in range(len(self.cards) - 1, 0, -1):
            j = random.randint(0, i)
            self.cards[i], self.cards[j] = self.cards[j], self.cards[i]
        self._dealt = 0

    def deal(self, n=1):
        if self._dealt + n > len(self.cards):
            raise ValueError("not enough cards left")
        out = self.cards[self._dealt:self._dealt + n]
        self._dealt += n         # deal by moving a cursor, do not mutate the list
        return out

class Hand:
    def __init__(self): self.cards = []
    def add(self, card): self.cards.append(card)

    def value(self):
        """Blackjack scoring - the ace rule is the whole exercise."""
        total = aces = 0
        for c in self.cards:
            if c.rank == "A":        total += 11; aces += 1
            elif c.rank in "JQK":    total += 10
            else:                    total += int(c.rank)
        while total > 21 and aces:   # downgrade ONE ace at a time, 11 -> 1
            total -= 10
            aces -= 1
        return total

    def is_bust(self):      return self.value() > 21
    def is_blackjack(self): return len(self.cards) == 2 and self.value() == 21

class Blackjack:
    """RULES live here so Deck and Card stay reusable for any card game."""
    def __init__(self, packs=6):
        self.deck = Deck(packs); self.deck.shuffle()
        self.player, self.dealer = Hand(), Hand()

    def opening_deal(self):
        for h in (self.player, self.dealer, self.player, self.dealer):
            h.add(self.deck.deal(1)[0])

    def hit(self, hand): hand.add(self.deck.deal(1)[0]); return hand.value()

    def dealer_plays(self):
        while self.dealer.value() < 17:      # house rule: stand on 17
            self.hit(self.dealer)
'''),
          example="Hand A + A + 9: all aces as 11 gives 11+11+9 = 31, bust, so knock 10 off one ace -> 21. A perfect hand that a per-ace if/else usually scores as 11 or 31.",
          pitfalls="Biased shuffle (swapping with any random index rather than a random index at or below i); putting blackjack scoring inside Card, which stops the deck being reused; mutable Card, so a card in two hands can be edited in one place; forgetting the shoe runs out with multiple packs.",
          followups="'Model splits and doubling down' - a player now has a LIST of hands, so the game loop iterates hands rather than assuming one. 'How would you test the shuffle?' Deal a fixed seed for determinism in unit tests, and separately run a chi-squared test over many shuffles to check the distribution is uniform."),

        Q("lld", "LLD: Design Splitwise (shared expense settlement)",
          "A great prompt because the object model is easy and one algorithm is genuinely interesting. NOUNS: User, Group, Expense, Split, Balance. THE MODEL: an Expense has a payer, an amount and a list of splits; the split TYPE varies (equal, exact amounts, percentage, shares) so it is a Strategy - that is the extension point and the interviewer is looking for it. Every expense updates a balance ledger, best stored as balance[a][b] = what a owes b, or more simply as one net figure per person (positive means they are owed money). THE HARD PART is 'simplify debts': with A owes B 10, B owes C 10, the naive answer is two payments, but the right answer is A pays C 10 - one payment. The general algorithm: compute every person's NET position, put the debtors in one heap and the creditors in another, then repeatedly match the largest debtor with the largest creditor and settle the smaller of the two amounts. That produces at most n-1 transactions for n people. Say clearly that finding the absolute minimum number of transactions is NP-hard (it is a partition problem), and that the greedy heap approach is the standard practical answer - naming the limit of your own solution is a strong signal. Also mention the rounding rule: cents do not divide by three, so split in integer cents and give the remainder to the payer, or the ledger drifts.",
          ["splitwise", "lld", "ood", "design", "greedy", "strategy", "amazon"],
          difficulty="Medium",
          frequency="Commonly asked at Amazon and by fintech teams; the debt-simplification part is the differentiator.",
          mnemonic="Expense = payer + amount + a SplitStrategy. Keep NET balances per person. To settle: max-heap of debtors, max-heap of creditors, match the two biggest and repeat - n-1 payments. Exact-minimum is NP-hard; say so.",
          code=_c('''
from abc import ABC, abstractmethod
from collections import defaultdict
import heapq

class SplitStrategy(ABC):
    @abstractmethod
    def split(self, amount_cents, participants, **kw) -> dict: ...

class EqualSplit(SplitStrategy):
    def split(self, amount_cents, participants, **kw):
        n = len(participants)
        base, rem = divmod(amount_cents, n)      # integer cents - never floats
        shares = {p: base for p in participants}
        # The leftover cents have to go SOMEWHERE or the ledger drifts.
        for p in participants[:rem]:
            shares[p] += 1
        return shares

class ExactSplit(SplitStrategy):
    def split(self, amount_cents, participants, amounts=None, **kw):
        if sum(amounts.values()) != amount_cents:
            raise ValueError("exact splits must add up to the total")
        return dict(amounts)

class PercentSplit(SplitStrategy):
    def split(self, amount_cents, participants, percents=None, **kw):
        if round(sum(percents.values()), 6) != 100:
            raise ValueError("percentages must sum to 100")
        shares = {p: amount_cents * percents[p] // 100 for p in participants}
        # Give any rounding remainder to the first participant.
        shares[participants[0]] += amount_cents - sum(shares.values())
        return shares

class ExpenseBook:
    def __init__(self):
        self.net = defaultdict(int)          # person -> cents (+ owed to them)

    def add_expense(self, payer, amount_cents, participants,
                    strategy: SplitStrategy, **kw):
        shares = strategy.split(amount_cents, participants, **kw)
        for person, owed in shares.items():
            if person == payer:
                continue
            self.net[person] -= owed         # they owe
            self.net[payer]  += owed         # payer is owed
        return shares

    def simplify(self):
        """Greedy settlement: at most n-1 payments."""
        debtors  = [(v, p) for p, v in self.net.items() if v < 0]   # v is negative
        creditors = [(-v, p) for p, v in self.net.items() if v > 0]
        heapq.heapify(debtors)               # most negative = biggest debtor first
        heapq.heapify(creditors)             # most negative of -v = biggest credit
        payments = []
        while debtors and creditors:
            d_amt, d = heapq.heappop(debtors)      # d_amt <= 0
            c_amt, c = heapq.heappop(creditors)    # c_amt <= 0
            pay = min(-d_amt, -c_amt)              # settle the smaller side fully
            payments.append((d, c, pay))
            if -d_amt > pay: heapq.heappush(debtors,  (d_amt + pay, d))
            if -c_amt > pay: heapq.heappush(creditors, (c_amt + pay, c))
        return payments

book = ExpenseBook()
book.add_expense("A", 3000, ["A", "B", "C"], EqualSplit())   # A paid 30.00 for 3
book.add_expense("B", 1500, ["B", "C"], EqualSplit())        # B paid 15.00 for 2
book.simplify()   # a short list of who pays whom, netted
'''),
          example="Dinner costs 30.00 split three ways: 3000 cents / 3 = 1000 each, no remainder. A 10.00 taxi split three ways is 1000/3 = 333 with a remainder of 1, so one person pays 334 - and the ledger stays exactly balanced instead of losing a cent per expense forever.",
          pitfalls="Floating-point money (0.1 + 0.2 != 0.3, and the ledger drifts) - always integer cents; recording every pairwise debt instead of net positions, which makes settlement quadratic; claiming your greedy settlement is provably minimal (it is not); forgetting that the payer is also usually a participant and must not owe themselves.",
          followups="'Support multiple currencies' - store the amount plus the currency plus the rate AT THE TIME of the expense, and settle per currency; never re-convert historical expenses at today's rate. 'How would you show a running balance per group?' Keep the net map per group as well as globally, since people expect to settle a trip without touching unrelated debts."),
    ]

    # ── More LLD prompts: infrastructure-flavoured and product-flavoured ──
    entries += [
        Q("lld", "LLD: Design a Rate Limiter",
          "Asked constantly because it is small enough to finish and rich enough to discuss. CLARIFY: per user or per IP or per API key, what limit, is a burst allowed, one server or many? The four algorithms, and when each is right. FIXED WINDOW - count requests per clock minute; trivial and cheap, but it allows a double burst at the boundary (100 requests at 12:00:59 and 100 more at 12:01:00 = 200 in one second). SLIDING WINDOW LOG - keep the timestamps of recent requests and drop the old ones; exact, but memory grows with traffic. SLIDING WINDOW COUNTER - weight the previous window's count by how much of it still overlaps; a good approximation with O(1) memory, and what most production systems use. TOKEN BUCKET - tokens refill at a steady rate up to a cap; a request spends one; this is the one to lead with because it allows a controlled BURST (the bucket capacity) while enforcing a long-run average, which is what APIs actually want. Implement token bucket lazily: do not run a background timer, just compute how many tokens have accrued since the last request from the elapsed time. Then the distributed follow-up: an in-process dict does not work across ten servers, so the state moves to Redis and the check-and-decrement must be atomic (a Lua script or INCR with an expiry).",
          ["rate-limiter", "lld", "ood", "token-bucket", "design", "amazon", "system"],
          difficulty="Medium",
          frequency="Very commonly asked at Amazon and Google, both as an LLD and inside system design.",
          mnemonic="Token bucket = a bucket refilling at r tokens/sec with a cap of b. Spend one per request, refuse when empty. Refill LAZILY from elapsed time - no timer thread. Fixed windows have the boundary-burst bug.",
          code=_c('''
import time, threading
from collections import deque

class TokenBucket:
    """Allows bursts up to `capacity`, long-run average of `rate` per second."""
    def __init__(self, rate, capacity):
        self.rate, self.capacity = rate, capacity
        self.tokens = float(capacity)          # start full
        self.last = time.monotonic()           # monotonic: immune to clock changes
        self.lock = threading.Lock()

    def allow(self, cost=1):
        with self.lock:                        # check-and-spend must be atomic
            now = time.monotonic()
            # LAZY REFILL: no timer thread, just credit the elapsed time.
            self.tokens = min(self.capacity,
                              self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False                       # 429 Too Many Requests

class SlidingWindowLog:
    """Exact, but memory is proportional to the number of allowed requests."""
    def __init__(self, limit, window_s):
        self.limit, self.window = limit, window_s
        self.hits = deque()
    def allow(self):
        now = time.monotonic()
        while self.hits and self.hits[0] <= now - self.window:
            self.hits.popleft()                # drop what has aged out
        if len(self.hits) < self.limit:
            self.hits.append(now); return True
        return False

class SlidingWindowCounter:
    """O(1) memory, and no boundary burst - the usual production choice."""
    def __init__(self, limit, window_s):
        self.limit, self.window = limit, window_s
        self.cur_start, self.cur, self.prev = 0.0, 0, 0
    def allow(self):
        now = time.monotonic()
        if now - self.cur_start >= self.window:      # roll over
            self.prev = self.cur if now - self.cur_start < 2 * self.window else 0
            self.cur, self.cur_start = 0, now
        overlap = 1 - (now - self.cur_start) / self.window   # how much of prev counts
        estimate = self.prev * overlap + self.cur
        if estimate < self.limit:
            self.cur += 1; return True
        return False

class RateLimiter:
    """One bucket per key (user / IP / API key), created on first sight."""
    def __init__(self, rate, capacity):
        self.rate, self.capacity = rate, capacity
        self.buckets, self.lock = {}, threading.Lock()
    def allow(self, key):
        with self.lock:
            b = self.buckets.get(key)
            if b is None:
                b = self.buckets[key] = TokenBucket(self.rate, self.capacity)
        return b.allow()

# Distributed version, in words: the bucket state (tokens, last_refill) lives in
# Redis under the key, and refill+spend run inside one Lua script so the whole
# check-and-decrement is atomic across every server.
'''),
          example="rate=10/s, capacity=50. An idle client has 50 tokens saved, so it can fire 50 requests instantly (the allowed burst), then is throttled to 10/s while the bucket refills. A fixed-window limiter of '50 per 5 seconds' would instead permit 100 requests across one window boundary.",
          pitfalls="Using time.time() instead of time.monotonic(), so an NTP correction can make elapsed time negative; a background refill thread per user (thousands of threads for nothing); an unbounded bucket dict, which leaks memory for one-off IPs - evict with an LRU or a TTL; forgetting the response contract (429 plus a Retry-After header).",
          followups="'Now across 10 servers' - move the state to Redis with an atomic Lua check-and-decrement; approximating by giving each server limit/10 is simpler but breaks under uneven load balancing. 'Different limits per tier?' The limiter takes (rate, capacity) from a policy lookup keyed by the caller's plan - config, not code."),

        Q("lld", "LLD: Design an in-memory Key-Value store with TTL (a mini Redis)",
          "A favourite because the naive answer works and the follow-ups expose whether you think about cost. Requirements: get, set with an optional expiry, delete, and eviction when full. THE FIRST DECISION is how expiry is enforced. Do not sweep every key on a timer - with a million keys that is a periodic stall. Use LAZY EXPIRY: store an expires_at with each entry, and on read, if it has passed, delete and report a miss. Then add a small ACTIVE sampler (Redis samples 20 random keys with a TTL a few times a second and deletes the expired ones) so keys nobody reads still get reclaimed - the combination is the real answer. THE SECOND DECISION is eviction when memory is full, and this is where the design earns its marks: make the policy pluggable (LRU, LFU, random) rather than hard-coded. LRU needs O(1) get and put, which means a hash map plus a doubly linked list (or Python's OrderedDict with move_to_end). THE THIRD is that a TTL heap gives you the soonest-expiring key in O(log n) if you want a background reaper, at the cost of keeping the heap in sync with overwrites - mention the trade rather than silently picking one.",
          ["kv-store", "cache", "ttl", "lru", "lld", "ood", "design", "amazon"],
          difficulty="Medium",
          frequency="Commonly asked at Amazon; the LRU half also appears as a pure coding question.",
          mnemonic="Lazy expiry on read + a random active sampler, not a full sweep. Eviction policy behind an interface. LRU = hash map + doubly linked list (OrderedDict.move_to_end) for O(1) get and put.",
          code=_c('''
import time, random, threading
from abc import ABC, abstractmethod
from collections import OrderedDict

class EvictionPolicy(ABC):
    @abstractmethod
    def on_access(self, key): ...
    @abstractmethod
    def on_insert(self, key): ...
    @abstractmethod
    def evict(self) -> str: ...          # returns the key to drop

class LRUPolicy(EvictionPolicy):
    """Least Recently Used. OrderedDict gives O(1) reorder."""
    def __init__(self): self.order = OrderedDict()
    def on_access(self, key):
        if key in self.order: self.order.move_to_end(key)     # most recent = last
    def on_insert(self, key): self.order[key] = True; self.order.move_to_end(key)
    def evict(self): return self.order.popitem(last=False)[0]  # oldest = first
    def forget(self, key): self.order.pop(key, None)

class LFUPolicy(EvictionPolicy):
    """Least Frequently Used - better for a stable hot set, worse for scans."""
    def __init__(self): self.counts = {}
    def on_access(self, key): self.counts[key] = self.counts.get(key, 0) + 1
    def on_insert(self, key): self.counts[key] = 1
    def evict(self): return min(self.counts, key=self.counts.get)
    def forget(self, key): self.counts.pop(key, None)

class KVStore:
    def __init__(self, capacity=1000, policy=None):
        self.capacity = capacity
        self.policy = policy or LRUPolicy()
        self.data = {}                    # key -> (value, expires_at or None)
        self.lock = threading.Lock()

    def set(self, key, value, ttl_seconds=None):
        with self.lock:
            expires = time.monotonic() + ttl_seconds if ttl_seconds else None
            if key not in self.data and len(self.data) >= self.capacity:
                victim = self.policy.evict()         # make room BEFORE inserting
                self.data.pop(victim, None)
            self.data[key] = (value, expires)
            self.policy.on_insert(key)

    def get(self, key, default=None):
        with self.lock:
            item = self.data.get(key)
            if item is None:
                return default
            value, expires = item
            # LAZY EXPIRY: pay the cost only when someone actually looks.
            if expires is not None and time.monotonic() > expires:
                del self.data[key]
                self.policy.forget(key)
                return default
            self.policy.on_access(key)
            return value

    def delete(self, key):
        with self.lock:
            self.data.pop(key, None); self.policy.forget(key)

    def sample_expired(self, n=20):
        """ACTIVE expiry, Redis-style: check a few random keys, not all of them.
        Keeps memory honest for keys nobody ever reads again."""
        with self.lock:
            now = time.monotonic()
            for key in random.sample(list(self.data), min(n, len(self.data))):
                _, expires = self.data[key]
                if expires is not None and now > expires:
                    del self.data[key]; self.policy.forget(key)
'''),
          example="set('session:42', user, ttl_seconds=900). Nobody reads it for an hour; the memory is only reclaimed when the sampler happens to pick it, or on the next read - both correct, and neither ever scans a million keys at once.",
          pitfalls="A background thread scanning every key each second (a stall proportional to the key count); evicting after inserting, so you can momentarily exceed capacity; forgetting to remove the evicted key from the policy's bookkeeping, which leaks; treating an expired-but-not-yet-deleted key as a hit; using wall-clock time for TTLs.",
          followups="'How do you make it persistent?' An append-only log of writes plus periodic snapshots - exactly Redis's AOF and RDB. 'Multiple threads?' One coarse lock is fine to start; the next step is sharding the keyspace into N maps each with its own lock, which is how real caches get concurrency."),

        Q("lld", "LLD: Design a Logging framework",
          "Small, and it exercises three patterns at once, which is why it gets asked. REQUIREMENTS: severity levels, multiple destinations (console, file, network), configurable formatting, and cheap enough that a disabled debug log costs almost nothing. THE DESIGN: a Logger takes a level and a message and, if the level passes the threshold, builds a LogRecord and hands it to every attached HANDLER (Strategy/Observer - console, rotating file, HTTP), each of which owns a FORMATTER (Strategy - plain text, JSON) and its own level threshold. Add a chain of loggers by name ('app.db' falls back to 'app') and you have essentially reproduced Python's logging module, which is a good thing to say out loud. THE PERFORMANCE POINT interviewers look for: check the level BEFORE formatting the message, because `log.debug(f'user {expensive()}')` evaluates the f-string even when debug is off - the fix is lazy formatting, passing the arguments and letting the handler interpolate only if the record survives. THE OTHER: file handlers need rotation (by size or by date) or they fill the disk, and a shared file handle needs a lock or two threads interleave half-lines.",
          ["logging", "lld", "ood", "design", "observer", "strategy"],
          difficulty="Easy",
          frequency="Commonly asked as a warm-up OOD; the lazy-formatting detail is the differentiator.",
          mnemonic="Logger -> LogRecord -> many Handlers, each with a Formatter and its own level. Check the level BEFORE building the string. Rotate files, lock the shared handle.",
          code=_c('''
from abc import ABC, abstractmethod
from enum import IntEnum
import threading, datetime as dt, json, os

class Level(IntEnum):                    # IntEnum so thresholds compare with >=
    DEBUG = 10; INFO = 20; WARNING = 30; ERROR = 40; CRITICAL = 50

class LogRecord:
    def __init__(self, level, msg, args, logger_name):
        self.level, self.msg, self.args = level, msg, args
        self.name, self.time = logger_name, dt.datetime.now()
    def message(self):
        # LAZY: interpolation happens here, only for records that survive.
        return self.msg % self.args if self.args else self.msg

class Formatter(ABC):
    @abstractmethod
    def format(self, record) -> str: ...

class TextFormatter(Formatter):
    def format(self, r):
        return f"{r.time:%Y-%m-%d %H:%M:%S} {r.level.name:<8} {r.name}: {r.message()}"

class JsonFormatter(Formatter):          # what log aggregators actually want
    def format(self, r):
        return json.dumps({"ts": r.time.isoformat(), "level": r.level.name,
                           "logger": r.name, "msg": r.message()})

class Handler(ABC):
    def __init__(self, level=Level.DEBUG, formatter=None):
        self.level = level
        self.formatter = formatter or TextFormatter()
        self.lock = threading.Lock()     # stop two threads interleaving a line
    def handle(self, record):
        if record.level >= self.level:   # per-handler threshold
            with self.lock:
                self.emit(self.formatter.format(record))
    @abstractmethod
    def emit(self, line): ...

class ConsoleHandler(Handler):
    def emit(self, line): print(line)

class RotatingFileHandler(Handler):
    """Rotate at max_bytes so logs cannot fill the disk."""
    def __init__(self, path, max_bytes=5_000_000, backups=3, **kw):
        super().__init__(**kw)
        self.path, self.max_bytes, self.backups = path, max_bytes, backups
    def emit(self, line):
        if os.path.exists(self.path) and os.path.getsize(self.path) >= self.max_bytes:
            for i in range(self.backups - 1, 0, -1):
                if os.path.exists(f"{self.path}.{i}"):
                    os.replace(f"{self.path}.{i}", f"{self.path}.{i+1}")
            os.replace(self.path, f"{self.path}.1")
        with open(self.path, "a") as f:
            f.write(line + "\\n")

class Logger:
    def __init__(self, name, level=Level.INFO):
        self.name, self.level, self.handlers = name, level, []
    def add_handler(self, h): self.handlers.append(h)

    def log(self, level, msg, *args):
        if level < self.level:
            return                       # THE FAST PATH: no record, no string
        record = LogRecord(level, msg, args, self.name)
        for h in self.handlers:
            h.handle(record)

    def debug(self, msg, *a):   self.log(Level.DEBUG, msg, *a)
    def info(self, msg, *a):    self.log(Level.INFO, msg, *a)
    def warning(self, msg, *a): self.log(Level.WARNING, msg, *a)
    def error(self, msg, *a):   self.log(Level.ERROR, msg, *a)

log = Logger("app.orders", Level.INFO)
log.add_handler(ConsoleHandler())
log.add_handler(RotatingFileHandler("app.log", level=Level.ERROR,
                                    formatter=JsonFormatter()))
log.info("order %s placed by %s", 1234, "venkat")   # lazy args, not an f-string
log.debug("payload %s", "...")                       # costs one integer compare
'''),
          example="`log.debug('user %s cart %s', uid, dump_cart())` still calls dump_cart() because Python evaluates arguments eagerly - the level check only saves the STRING FORMATTING. If the argument itself is expensive, guard it: `if log.isEnabledFor(DEBUG): ...`. Being precise about which cost you saved is the strong version of this answer.",
          pitfalls="Formatting the message before the level check; one lock for the whole logger instead of per handler, so a slow network handler blocks the console; no rotation; logging secrets or personal data (say that redaction belongs in a formatter); a synchronous network handler on the request path, which turns a logging outage into an application outage.",
          followups="'How do you avoid slowing the request path?' A queue handler: the request thread appends to an in-memory queue and a background thread drains it, accepting that a crash can lose the tail. 'How do you correlate logs across services?' A request/trace id propagated in the context and included by the formatter in every line."),

        Q("lld", "LLD: Design a Movie Ticket Booking system (BookMyShow)",
          "The interesting part is not the object model - it is the concurrency, and the interviewer will get there within five minutes. NOUNS: City, Cinema, Screen, Seat, Movie, Show, Booking, Payment. THE MODEL: a Show ties a Movie to a Screen at a time; seat availability is per SHOW, not per screen (the same physical seat is free for the 6pm and taken for the 9pm), which is the modelling detail candidates most often get wrong. THE CONCURRENCY, in three stages, and you should present it as a progression. (1) Two users click the same seat - the check-and-set must be atomic, so a per-show lock or a conditional database update. (2) Users need time to pay, so a booking is a two-phase thing: HOLD the seats with a short expiry (typically 5-10 minutes), then CONFIRM on payment; an expired hold must return the seats automatically, which needs either a background sweeper or a lazy check treating any hold past its expiry as free. (3) Across many servers the in-process lock is useless, so the hold has to live in the shared store - `UPDATE seats SET held_by=?, hold_expires=? WHERE show_id=? AND seat_id=? AND (held_by IS NULL OR hold_expires < now())` returning a row count is the whole solution in one statement. Also mention that seat selection should be idempotent by a request id, because users double-click.",
          ["booking", "bookmyshow", "lld", "ood", "concurrency", "design", "amazon"],
          difficulty="Hard",
          frequency="Very commonly asked at Amazon and Indian product companies; the seat-locking follow-up is the point of the question.",
          mnemonic="Availability is per SHOW, not per screen. Booking = HOLD with an expiry, then CONFIRM on payment. The atomic step is a conditional update: take the seat only if it is free or its hold has expired.",
          code=_c('''
import threading, time, itertools
from enum import Enum

class SeatState(Enum):
    FREE = "free"; HELD = "held"; BOOKED = "booked"

class Seat:
    def __init__(self, seat_id, row, number, tier="regular"):
        self.id, self.row, self.number, self.tier = seat_id, row, number, tier

class Show:
    """Availability lives HERE: the same seat is free at 6pm and sold at 9pm."""
    HOLD_SECONDS = 300
    def __init__(self, show_id, movie, screen, start_time, seats):
        self.id, self.movie, self.screen, self.start = show_id, movie, screen, start_time
        self.seats = {s.id: s for s in seats}
        self.state = {s.id: [SeatState.FREE, None, 0.0] for s in seats}  # state,user,expiry
        self.lock = threading.Lock()

    def _effective(self, seat_id, now):
        """A hold past its expiry counts as FREE - lazy expiry, no sweeper needed."""
        state, user, expires = self.state[seat_id]
        if state == SeatState.HELD and now > expires:
            return SeatState.FREE, None, 0.0
        return state, user, expires

    def hold(self, seat_ids, user):
        now = time.monotonic()
        with self.lock:                         # check ALL, then take ALL
            for sid in seat_ids:
                st, _, _ = self._effective(sid, now)
                if st != SeatState.FREE:
                    raise ValueError(f"seat {sid} is not available")
            expiry = now + self.HOLD_SECONDS
            for sid in seat_ids:
                self.state[sid] = [SeatState.HELD, user, expiry]
            return expiry                       # the client shows a countdown

    def confirm(self, seat_ids, user):
        now = time.monotonic()
        with self.lock:
            for sid in seat_ids:
                st, holder, _ = self._effective(sid, now)
                if st != SeatState.HELD or holder != user:
                    raise ValueError("hold expired - please select seats again")
            for sid in seat_ids:
                self.state[sid] = [SeatState.BOOKED, user, 0.0]
        return Booking(user, self, seat_ids)

    def release(self, seat_ids, user):          # user cancelled before paying
        with self.lock:
            for sid in seat_ids:
                if self.state[sid][1] == user and self.state[sid][0] == SeatState.HELD:
                    self.state[sid] = [SeatState.FREE, None, 0.0]

    def available(self):
        now = time.monotonic()
        return [sid for sid in self.state if self._effective(sid, now)[0] == SeatState.FREE]

class Booking:
    _ids = itertools.count(1)
    def __init__(self, user, show, seat_ids):
        self.id, self.user, self.show, self.seats = next(Booking._ids), user, show, list(seat_ids)

# Multi-server version - the same logic as ONE atomic statement:
#   UPDATE seats SET held_by = :u, hold_expires = :t
#    WHERE show_id = :s AND seat_id IN :ids
#      AND (held_by IS NULL OR hold_expires < now())
#   -- if the affected row count != len(ids), someone beat you: roll back.
'''),
          example="Two users select seat A5 for the 9pm show at the same instant. Both threads enter hold(); the lock serialises them; the first sets HELD with a 5-minute expiry, the second sees HELD and gets 'not available'. If the first never pays, the expiry makes A5 effectively FREE again with no cleanup job required.",
          pitfalls="Modelling seat availability on the Screen rather than the Show; holding seats forever when payment is abandoned; checking availability and then booking in two separate steps without a lock; partially holding a group of seats (hold all or none - check every seat first, as above); no idempotency, so a double-clicked Pay creates two bookings.",
          followups="'How do you stop bots grabbing every seat?' Rate-limit holds per user, cap concurrent holds, and require a CAPTCHA for large selections. 'How would you scale the seat map read?' Cache the availability per show with a short TTL, and accept that the definitive check happens at hold time - a stale seat map is fine, a stale booking is not."),

        Q("lld", "LLD: Design an in-memory File System",
          "A Google favourite because it looks like a data-structure problem and is really a design problem. REQUIREMENTS: mkdir, addContentToFile, readContentFromFile, ls (listing a directory sorted, or the file name if the path is a file). THE MODEL: a single Node type with an is_file flag and a children dict, or - better for an OOD round - an abstract Entry with File and Directory subclasses; the Composite pattern, where a Directory holds Entries and both expose size() and name(), so a directory's size is the sum of its children's and the recursion is free. THE MECHANIC everyone must get right: paths are resolved by splitting on '/' and walking the children dict from the root, creating intermediate directories only when the operation says to (mkdir -p semantics) and otherwise raising. Keep children in a dict for O(1) lookup and sort only when listing. THE FOLLOW-UPS are where it gets interesting: adding metadata (timestamps, permissions) is a field on Entry; adding a search by name means an auxiliary index, because otherwise it is a full traversal; and 'how would you make this a real file system?' opens up blocks, inodes and journalling - worth naming even if you do not design them.",
          ["file-system", "composite", "lld", "ood", "google", "design", "tree"],
          difficulty="Medium",
          frequency="Commonly asked at Google (it is also a well-known LeetCode-style design problem).",
          mnemonic="Composite pattern: Directory holds Entries, File is a leaf, both have name() and size(). Split the path on '/', walk the children dicts. Dict for lookup, sort only when listing.",
          code=_c('''
from abc import ABC, abstractmethod
import datetime as dt

class Entry(ABC):
    """Common face for files and directories - the Composite pattern."""
    def __init__(self, name, parent=None):
        self.name, self.parent = name, parent
        self.created = self.modified = dt.datetime.now()
    @abstractmethod
    def size(self): ...
    def path(self):
        parts, node = [], self
        while node and node.parent is not None:
            parts.append(node.name); node = node.parent
        return "/" + "/".join(reversed(parts))

class File(Entry):                       # LEAF
    def __init__(self, name, parent=None):
        super().__init__(name, parent); self.content = ""
    def size(self): return len(self.content)
    def append(self, text):
        self.content += text; self.modified = dt.datetime.now()

class Directory(Entry):                  # COMPOSITE
    def __init__(self, name, parent=None):
        super().__init__(name, parent); self.children = {}     # name -> Entry
    def size(self):
        return sum(c.size() for c in self.children.values())   # recursion, free

class FileSystem:
    def __init__(self):
        self.root = Directory("", None)

    def _walk(self, path, create=False):
        node = self.root
        for part in [p for p in path.split("/") if p]:
            if part not in node.children:
                if not create:
                    raise FileNotFoundError(path)
                node.children[part] = Directory(part, node)     # mkdir -p
            node = node.children[part]
            if isinstance(node, File):
                raise NotADirectoryError(node.path())
        return node

    def mkdir(self, path):
        self._walk(path, create=True)

    def add_content(self, path, text):
        parent_path, _, name = path.rpartition("/")
        parent = self._walk(parent_path or "/", create=True)
        entry = parent.children.get(name)
        if entry is None:
            entry = parent.children[name] = File(name, parent)   # create on write
        if not isinstance(entry, File):
            raise IsADirectoryError(path)
        entry.append(text)

    def read(self, path):
        parent_path, _, name = path.rpartition("/")
        parent = self._walk(parent_path or "/")
        entry = parent.children.get(name)
        if not isinstance(entry, File):
            raise FileNotFoundError(path)
        return entry.content

    def ls(self, path):
        parent_path, _, name = path.rpartition("/")
        node = self._walk(parent_path or "/") if name else self.root
        entry = node.children.get(name) if name else self.root
        if entry is None:
            raise FileNotFoundError(path)
        if isinstance(entry, File):
            return [entry.name]                        # ls on a file: its own name
        return sorted(entry.children)                  # sort only at listing time

fs = FileSystem()
fs.mkdir("/a/b/c")
fs.add_content("/a/b/c/notes.txt", "hello ")
fs.add_content("/a/b/c/notes.txt", "world")
fs.read("/a/b/c/notes.txt")     # "hello world"
fs.ls("/a/b/c")                 # ["notes.txt"]
fs.root.size()                  # 11 - summed recursively through the tree
'''),
          example="`fs.root.size()` needs no special code: Directory.size() sums its children, each of which is either a File returning its content length or another Directory recursing again. That is the entire value of the Composite pattern in one line.",
          pitfalls="Keeping children in a list, making every lookup a linear scan; sorting on insert instead of on ls (you list far less often than you write); no distinction between a file and a directory at the same path; failing on the root path '/' and on trailing slashes - test both; unbounded recursion on a symlink loop if you add symlinks.",
          followups="'Add search by filename' - a dict from name to a list of entries, maintained on create/delete, since otherwise every search is a full traversal. 'How does a real file system differ?' Content lives in fixed-size blocks referenced by an inode, directories are just files mapping names to inode numbers, and a journal makes multi-block updates crash-safe."),

        Q("lld", "LLD: Design a Notification service (email, SMS, push)",
          "A compact prompt that lets you show three patterns and a little distributed-systems judgement. REQUIREMENTS: send a notification through one or more channels, respect user preferences, do not spam, survive a provider outage. THE DESIGN: a Notification value object (recipient, template id, data), a Channel interface with EmailChannel, SmsChannel, PushChannel behind it (Strategy), a factory or registry to construct them by name, and a NotificationService that looks up the user's preferences and dispatches to the selected channels. THE THINGS THAT MAKE IT A GOOD ANSWER, none of which are about class shapes. (1) Send ASYNCHRONOUSLY - the caller enqueues and returns, because an SMS provider taking three seconds must never be on your checkout request path. (2) RETRY with exponential backoff plus jitter, and a dead-letter queue for what still fails; then note that retries demand IDEMPOTENCY, so every notification carries a key and the channel refuses a duplicate. (3) Templates and localisation belong in a renderer, not in the channel. (4) Preferences and quiet hours are a policy check before dispatch, and a rate limit per user stops a retry loop texting someone forty times. Saying 'queue, retry, idempotency key, dead-letter' is what separates this from a class diagram.",
          ["notification", "lld", "ood", "design", "strategy", "factory", "queue", "amazon"],
          difficulty="Medium",
          frequency="Commonly asked at Amazon - it maps directly onto SNS/SES-style internal services.",
          mnemonic="Channel interface + registry, preferences checked before dispatch, ENQUEUE rather than send inline, retry with backoff and jitter, idempotency key so retries do not double-send, dead-letter what will not go.",
          code=_c('''
from abc import ABC, abstractmethod
from collections import deque
import random, time

class Notification:
    def __init__(self, key, user_id, template, data, channels=None):
        self.key = key                 # IDEMPOTENCY KEY - retries reuse it
        self.user_id, self.template, self.data = user_id, template, data
        self.channels = channels       # None = use the user's preferences

class Channel(ABC):
    name = "base"
    @abstractmethod
    def send(self, address, subject, body): ...

class EmailChannel(Channel):
    name = "email"
    def send(self, address, subject, body): return True     # SES call

class SmsChannel(Channel):
    name = "sms"
    def send(self, address, subject, body): return True     # Twilio call

class PushChannel(Channel):
    name = "push"
    def send(self, address, subject, body): return True     # FCM/APNs call

class TemplateRenderer:
    """Localisation and copy live here - channels stay dumb pipes."""
    def __init__(self, templates): self.templates = templates
    def render(self, template, data, locale="en"):
        subject, body = self.templates[(template, locale)]
        return subject.format(**data), body.format(**data)

class NotificationService:
    def __init__(self, renderer, prefs, channels):
        self.renderer, self.prefs = renderer, prefs
        self.channels = {c.name: c for c in channels}       # registry
        self.queue, self.dead_letter = deque(), []
        self.sent_keys = set()                              # idempotency ledger

    def notify(self, n: Notification):
        self.queue.append(n)          # ENQUEUE and return - never send inline

    def _wanted(self, n):
        p = self.prefs.get(n.user_id, {})
        wanted = n.channels or p.get("channels", ["email"])
        if p.get("quiet_hours") and time.localtime().tm_hour in p["quiet_hours"]:
            wanted = [c for c in wanted if c != "sms"]      # policy, not code
        return wanted

    def worker_tick(self, max_attempts=5):
        """A background worker drains the queue with backoff + dead-lettering."""
        while self.queue:
            n = self.queue.popleft()
            for ch_name in self._wanted(n):
                dedupe = (n.key, ch_name)
                if dedupe in self.sent_keys:
                    continue                                # a retry, already sent
                subject, body = self.renderer.render(n.template, n.data)
                channel = self.channels[ch_name]
                for attempt in range(max_attempts):
                    try:
                        if channel.send(self.prefs[n.user_id][ch_name], subject, body):
                            self.sent_keys.add(dedupe)
                            break
                    except Exception:
                        if attempt == max_attempts - 1:
                            self.dead_letter.append((n, ch_name))   # inspect later
                        else:
                            # Exponential backoff WITH JITTER, so a provider
                            # outage does not make every worker retry in lockstep.
                            time.sleep((2 ** attempt) * 0.1 * (0.5 + random.random()))
'''),
          example="An order-confirmation notification with key 'order-1234-confirm'. The SMS provider times out but actually delivered; the retry checks ('order-1234-confirm', 'sms') in the ledger... and only skips if the first attempt recorded success. Where the provider itself is unreliable, you also pass the key to the provider so IT deduplicates - worth saying that at-least-once delivery makes idempotency the receiver's job too.",
          pitfalls="Sending synchronously inside the request; retrying without an idempotency key, which double-charges the user's attention; retrying in a tight loop with no backoff and taking down a recovering provider; putting template text inside channel classes; no dead-letter queue, so permanently-failing messages retry forever.",
          followups="'How would you support scheduled or digest notifications?' A due_at column and a scheduler that enqueues when due; digests aggregate per user over a window. 'How do you avoid notification fatigue?' A per-user rate limit and a priority level, dropping or batching low-priority messages when the user is over budget."),

        Q("lld", "LLD: Design Snake and Ladder (and what it really tests)",
          "A deceptively simple prompt used to check that you separate the BOARD, the RULES and the GAME LOOP, and that you handle the awkward edge cases. THE MODEL: a Board holding a jumps dict (start square to end square) which covers snakes and ladders uniformly - a snake is just a jump where the end is lower - a Dice with a configurable number of faces, a Player with a position, and a Game that runs the loop. THE INSIGHT worth stating: snakes and ladders are the SAME data structure, and modelling them as two classes is a small red flag. THE EDGE CASES that separate answers: an overshoot at the top (either stay put or bounce back - ask which), chained jumps (landing on a ladder that ends at the head of a snake - decide whether to resolve repeatedly and cap the chain to avoid an infinite loop from bad board data), and an extra turn on a six with a cap so a lucky player cannot loop forever. VALIDATION is the other half: no square may be the start of two jumps, no snake may start at square 1 or end at the last square, and the destination must be within bounds - checking board data at construction is exactly the kind of defensive thinking Amazon looks for.",
          ["snake-and-ladder", "game", "lld", "ood", "design"],
          difficulty="Easy",
          frequency="Commonly asked as a warm-up OOD, especially in campus and SDE-1 loops.",
          mnemonic="Snakes and ladders are ONE dict: square -> destination. Validate the board at construction. Decide the overshoot rule and cap chained jumps and six-rolls, or you can loop forever.",
          code=_c('''
import random
from collections import deque

class Dice:
    def __init__(self, faces=6, count=1): self.faces, self.count = faces, count
    def roll(self): return sum(random.randint(1, self.faces) for _ in range(self.count))

class Board:
    def __init__(self, size=100, jumps=None):
        self.size = size
        self.jumps = dict(jumps or {})       # snakes AND ladders - one structure
        self._validate()

    def _validate(self):
        for start, end in self.jumps.items():
            if not (1 <= start <= self.size and 1 <= end <= self.size):
                raise ValueError(f"jump {start}->{end} is off the board")
            if start == end:
                raise ValueError("a jump must move you")
            if start == self.size:
                raise ValueError("nothing can start on the winning square")
        # A square cannot be the head of two jumps - dict keys already enforce it.

    def resolve(self, square, max_chain=10):
        """Follow chained ladders/snakes, capped so bad data cannot hang us."""
        seen = 0
        while square in self.jumps and seen < max_chain:
            square = self.jumps[square]; seen += 1
        return square

class Player:
    def __init__(self, name): self.name, self.position = name, 0

class Game:
    def __init__(self, board, players, dice=None, bounce_back=True):
        self.board, self.dice = board, dice or Dice()
        self.players = deque(Player(p) for p in players)
        self.bounce_back = bounce_back        # ASK the interviewer which rule
        self.winner = None

    def take_turn(self, max_sixes=3):
        p = self.players[0]
        sixes = 0
        while True:
            roll = self.dice.roll()
            target = p.position + roll
            if target > self.board.size:
                # Overshoot: either stay put, or bounce back off the end.
                target = (2 * self.board.size - target) if self.bounce_back else p.position
            p.position = self.board.resolve(target)
            if p.position == self.board.size:
                self.winner = p; return p
            if roll == self.dice.faces and sixes < max_sixes - 1:
                sixes += 1; continue          # extra turn, but capped
            break
        self.players.rotate(-1)               # next player
        return None

board = Board(100, {2: 38, 7: 14, 16: 6, 46: 25, 49: 11, 62: 19, 87: 24, 99: 78})
game = Game(board, ["Asha", "Ben"])
while not game.winner:
    game.take_turn()
'''),
          example="A player on 95 rolls a 6, so target is 101. With bounce_back the position becomes 2*100 - 101 = 99; without it, they stay on 95 and must roll exactly 5. Both are real house rules, which is why you ASK rather than assume - and asking is itself a scored behaviour.",
          pitfalls="Separate Snake and Ladder classes doing identical work; not validating the board, so a jump to square 105 silently corrupts the game; infinite loops from a chained jump cycle or unlimited extra turns on a six; putting the dice roll inside Player, which makes the game untestable - inject a fake dice that returns a fixed sequence.",
          followups="'Make it deterministic for tests' - inject the Dice, and pass a fake that yields a scripted list of rolls. 'What is the expected number of turns to finish?' A Markov chain over the 101 states, or a Monte Carlo simulation - a nice segue if the interviewer is mathematically inclined."),

        Q("lld", "LLD: Design an e-commerce Order and Inventory model",
          "This is the LLD that most resembles real work, and Amazon asks it in some form constantly. NOUNS: Product, InventoryItem, Cart, CartLine, Order, OrderLine, Payment, Shipment, Address. THE DECISIONS THAT MATTER, and they are all about money and truth. (1) SNAPSHOT THE PRICE onto the order line at checkout. If OrderLine holds a reference to Product and reads product.price, then tomorrow's price change silently rewrites yesterday's invoices - a genuine accounting bug that candidates create constantly. Same for the shipping address: copy it, do not point at the user's current address. (2) INVENTORY IS RESERVED, NOT DECREMENTED, at checkout: available = on_hand - reserved. A reservation has an expiry, is confirmed when payment succeeds, and is released when payment fails or the cart is abandoned. (3) The ORDER IS A STATE MACHINE (Pending -> Paid -> Packed -> Shipped -> Delivered, with Cancelled and Returned branches), and which transitions are legal is exactly the State pattern's job. (4) Prices, discounts and taxes are separate concerns - a PricingEngine applying a list of discount rules keeps the arithmetic out of Cart, and the total should be computed once and stored, not recomputed on every page load.",
          ["ecommerce", "order", "inventory", "lld", "ood", "design", "amazon", "state"],
          difficulty="Medium",
          frequency="Very commonly asked at Amazon - closest to the actual domain.",
          mnemonic="Snapshot the price and address onto the order. RESERVE inventory (available = on_hand - reserved), do not decrement. Order lifecycle = a state machine. Discounts in a pricing engine, not in Cart.",
          code=_c('''
from abc import ABC, abstractmethod
from enum import Enum
import threading, itertools, datetime as dt

class OrderStatus(Enum):
    PENDING = "pending"; PAID = "paid"; PACKED = "packed"
    SHIPPED = "shipped"; DELIVERED = "delivered"
    CANCELLED = "cancelled"; RETURNED = "returned"

LEGAL = {                                    # the state machine, as data
    OrderStatus.PENDING:   {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID:      {OrderStatus.PACKED, OrderStatus.CANCELLED},
    OrderStatus.PACKED:    {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED:   {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: {OrderStatus.RETURNED},
    OrderStatus.CANCELLED: set(), OrderStatus.RETURNED: set(),
}

class Product:
    def __init__(self, sku, name, price_cents):
        self.sku, self.name, self.price_cents = sku, name, price_cents

class InventoryItem:
    """available = on_hand - reserved. Reservations expire."""
    def __init__(self, sku, on_hand):
        self.sku, self.on_hand, self.reserved = sku, on_hand, 0
        self.lock = threading.Lock()
    def available(self): return self.on_hand - self.reserved

class Inventory:
    def __init__(self, items): self.items = {i.sku: i for i in items}
    def reserve(self, sku, qty):
        item = self.items[sku]
        with item.lock:                       # check-and-reserve, atomically
            if item.available() < qty:
                raise ValueError(f"only {item.available()} left of {sku}")
            item.reserved += qty
    def confirm(self, sku, qty):              # payment succeeded: goods leave
        item = self.items[sku]
        with item.lock:
            item.reserved -= qty; item.on_hand -= qty
    def release(self, sku, qty):              # payment failed / cart abandoned
        item = self.items[sku]
        with item.lock:
            item.reserved -= qty

class OrderLine:
    """PRICE IS COPIED, not referenced - yesterday's invoice must not change."""
    def __init__(self, product, qty):
        self.sku, self.name = product.sku, product.name
        self.unit_price_cents = product.price_cents      # the snapshot
        self.qty = qty
    def subtotal(self): return self.unit_price_cents * self.qty

class DiscountRule(ABC):
    @abstractmethod
    def apply(self, lines, subtotal) -> int: ...          # returns cents off

class PercentOff(DiscountRule):
    def __init__(self, pct, min_spend=0): self.pct, self.min_spend = pct, min_spend
    def apply(self, lines, subtotal):
        return subtotal * self.pct // 100 if subtotal >= self.min_spend else 0

class PricingEngine:
    def __init__(self, rules=(), tax_pct=23):
        self.rules, self.tax_pct = list(rules), tax_pct
    def total(self, lines):
        subtotal = sum(l.subtotal() for l in lines)
        discount = sum(r.apply(lines, subtotal) for r in self.rules)
        taxed = subtotal - discount
        return subtotal, discount, taxed * self.tax_pct // 100, \\
               taxed + taxed * self.tax_pct // 100

class Order:
    _ids = itertools.count(1)
    def __init__(self, user, lines, address, pricing: PricingEngine):
        self.id, self.user, self.lines = next(Order._ids), user, lines
        self.address = dict(address)          # COPIED, not a live reference
        self.placed_at = dt.datetime.now()
        (self.subtotal, self.discount,
         self.tax, self.total) = pricing.total(lines)     # computed ONCE, stored
        self.status = OrderStatus.PENDING

    def transition(self, new: OrderStatus):
        if new not in LEGAL[self.status]:
            raise ValueError(f"cannot go {self.status.value} -> {new.value}")
        self.status = new

class Checkout:
    def __init__(self, inventory, pricing):
        self.inventory, self.pricing = inventory, pricing
    def place(self, user, cart_items, address):
        reserved = []
        try:
            for product, qty in cart_items:
                self.inventory.reserve(product.sku, qty)     # reserve everything
                reserved.append((product.sku, qty))
            lines = [OrderLine(p, q) for p, q in cart_items]
            return Order(user, lines, address, self.pricing)
        except Exception:
            for sku, qty in reserved:
                self.inventory.release(sku, qty)             # all-or-nothing
            raise
'''),
          example="Product price rises from 20.00 to 25.00 overnight. Because OrderLine copied unit_price_cents at checkout, yesterday's order still shows 20.00 on the invoice and in the refund. Had it held a Product reference, every historical order and every accounting report would silently change - the bug is invisible until an auditor finds it.",
          pitfalls="Storing a Product reference on the order line; decrementing stock at add-to-cart (one abandoned cart takes the last unit off sale); recomputing the total on every read so a promotion ending changes an old order; allowing any status to move to any other; floating-point money instead of integer cents; releasing reservations only on explicit cancel, so abandoned carts hold stock forever - they need an expiry.",
          followups="'Two customers buy the last unit simultaneously' - the reserve() check-and-increment must be atomic; in a database that is `UPDATE inventory SET reserved = reserved + ? WHERE sku = ? AND on_hand - reserved >= ?` and you check the row count. 'How would you handle partial shipment?' Shipment becomes its own entity referencing a subset of order lines, and the order status becomes derived from its shipments rather than a single flag."),
    ]

    return entries
