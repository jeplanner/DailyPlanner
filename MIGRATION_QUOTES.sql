-- ============================================================
--  DailyPlanner — QUOTES library
--
--  The Eisenhower page renders a daily motivational quote — until now
--  it was a hardcoded JS array of 41 entries. This migration moves
--  the corpus to the database, expands it to ~120 curated entries
--  across 10 categories, and attaches structured metadata so future
--  features (filter by category, "show me only stoic", weekly theme)
--  can drop in cheaply.
--
--  Schema:
--    quotes(id, text, author, category, tags[], source, era,
--           is_active, created_at)
--
--  Categories used here:
--    action, discipline, resilience, wisdom, leadership, creativity,
--    focus, courage, growth, time
--
--  Safe to re-run — the seed block guards on (count = 0) so a
--  re-apply doesn't duplicate.
-- ============================================================

create table if not exists quotes (
  id          uuid primary key default gen_random_uuid(),
  text        text not null,
  author      text,
  category    text not null,
  tags        text[] default '{}',
  source      text,
  era         text,
  is_active   boolean default true,
  created_at  timestamptz default now()
);

create index if not exists quotes_category_idx
  on quotes (category) where is_active = true;
create index if not exists quotes_active_idx
  on quotes (is_active);


-- ── Seed: only when the table is empty so a re-run doesn't duplicate.
do $$
begin
  if (select count(*) from quotes) = 0 then
    insert into quotes (text, author, category, tags, era) values

    -- ── ACTION (getting started, shipping, doing) ──────────
    ('The secret of getting ahead is getting started.', 'Mark Twain', 'action', array['start'], 'modern'),
    ('Action is the foundational key to all success.', 'Pablo Picasso', 'action', array['start'], 'modern'),
    ('You don''t have to be great to start, but you have to start to be great.', 'Zig Ziglar', 'action', array['start'], 'modern'),
    ('Start where you are. Use what you have. Do what you can.', 'Arthur Ashe', 'action', array['start','enough'], 'modern'),
    ('A year from now you will wish you had started today.', 'Karen Lamb', 'action', array['start','time'], 'modern'),
    ('The man who moves a mountain begins by carrying away small stones.', 'Confucius', 'action', array['start','small'], 'ancient'),
    ('Done is better than perfect.', 'Sheryl Sandberg', 'action', array['ship'], 'modern'),
    ('Well done is better than well said.', 'Benjamin Franklin', 'action', array['ship'], 'classical'),
    ('Make each day your masterpiece.', 'John Wooden', 'action', array['ship'], 'modern'),
    ('Amateurs sit and wait for inspiration. The rest of us just get up and go to work.', 'Stephen King', 'action', array['ship','craft'], 'modern'),
    ('You miss 100% of the shots you don''t take.', 'Wayne Gretzky', 'action', array['risk'], 'modern'),
    ('Great things are done by a series of small things brought together.', 'Vincent Van Gogh', 'action', array['small'], 'classical'),
    ('It always seems impossible until it''s done.', 'Nelson Mandela', 'action', array['hope'], 'modern'),
    ('The journey of a thousand miles begins with a single step.', 'Lao Tzu', 'action', array['start','small'], 'ancient'),

    -- ── DISCIPLINE (habits, consistency, systems) ──────────
    ('We are what we repeatedly do. Excellence, then, is not an act, but a habit.', 'Will Durant', 'discipline', array['habit','excellence'], 'modern'),
    ('Quality is not an act, it is a habit.', 'Aristotle', 'discipline', array['habit','craft'], 'ancient'),
    ('You do not rise to the level of your goals. You fall to the level of your systems.', 'James Clear', 'discipline', array['systems'], 'modern'),
    ('What we do every day matters more than what we do once in a while.', 'Gretchen Rubin', 'discipline', array['habit'], 'modern'),
    ('Discipline is choosing between what you want now and what you want most.', 'Abraham Lincoln', 'discipline', array['choice'], 'classical'),
    ('Motivation is what gets you started. Habit is what keeps you going.', 'Jim Rohn', 'discipline', array['habit'], 'modern'),
    ('Small daily improvements are the key to staggering long-term results.', 'Robin Sharma', 'discipline', array['compounding'], 'modern'),
    ('Success is the sum of small efforts, repeated day in and day out.', 'Robert Collier', 'discipline', array['compounding'], 'modern'),
    ('Energy and persistence conquer all things.', 'Benjamin Franklin', 'discipline', array['persistence'], 'classical'),
    ('Either you run the day, or the day runs you.', 'Jim Rohn', 'discipline', array['ownership'], 'modern'),
    ('The harder I work, the luckier I get.', 'Samuel Goldwyn', 'discipline', array['effort','luck'], 'modern'),
    ('How we spend our days is, of course, how we spend our lives.', 'Annie Dillard', 'discipline', array['days','life'], 'modern'),
    ('Discipline equals freedom.', 'Jocko Willink', 'discipline', array['freedom'], 'modern'),

    -- ── RESILIENCE (bouncing back, persistence, failure) ──────
    ('Fall seven times, stand up eight.', 'Japanese Proverb', 'resilience', array['persistence'], 'ancient'),
    ('It does not matter how slowly you go as long as you do not stop.', 'Confucius', 'resilience', array['pace'], 'ancient'),
    ('Don''t watch the clock; do what it does. Keep going.', 'Sam Levenson', 'resilience', array['persistence'], 'modern'),
    ('The best way out is always through.', 'Robert Frost', 'resilience', array['through'], 'modern'),
    ('Our greatest weakness lies in giving up. The most certain way to succeed is always to try just one more time.', 'Thomas Edison', 'resilience', array['persistence'], 'classical'),
    ('I have not failed. I''ve just found 10,000 ways that won''t work.', 'Thomas Edison', 'resilience', array['failure'], 'classical'),
    ('Success is going from failure to failure without losing your enthusiasm.', 'Winston Churchill', 'resilience', array['failure'], 'modern'),
    ('When you come to the end of your rope, tie a knot and hang on.', 'Franklin D. Roosevelt', 'resilience', array['hang on'], 'modern'),
    ('Tough times never last, but tough people do.', 'Robert H. Schuller', 'resilience', array['adversity'], 'modern'),
    ('Persistence is to the character of man as carbon is to steel.', 'Napoleon Hill', 'resilience', array['persistence'], 'modern'),
    ('Courage doesn''t always roar. Sometimes courage is the quiet voice at the end of the day saying, ''I will try again tomorrow.''', 'Mary Anne Radmacher', 'resilience', array['courage','quiet'], 'modern'),
    ('Out of the mountain of despair, a stone of hope.', 'Martin Luther King Jr.', 'resilience', array['hope'], 'modern'),
    ('In the middle of difficulty lies opportunity.', 'Albert Einstein', 'resilience', array['opportunity'], 'classical'),

    -- ── WISDOM (philosophy, stoic, perspective) ──────────────
    ('We suffer more often in imagination than in reality.', 'Seneca', 'wisdom', array['stoic','worry'], 'ancient'),
    ('You have power over your mind — not outside events. Realize this, and you will find strength.', 'Marcus Aurelius', 'wisdom', array['stoic','control'], 'ancient'),
    ('It is not death that a man should fear, but he should fear never beginning to live.', 'Marcus Aurelius', 'wisdom', array['stoic','time'], 'ancient'),
    ('He who is not contented with what he has, would not be contented with what he would like to have.', 'Socrates', 'wisdom', array['contentment'], 'ancient'),
    ('Knowing yourself is the beginning of all wisdom.', 'Aristotle', 'wisdom', array['self'], 'ancient'),
    ('No man ever steps in the same river twice.', 'Heraclitus', 'wisdom', array['change'], 'ancient'),
    ('The unexamined life is not worth living.', 'Socrates', 'wisdom', array['reflection'], 'ancient'),
    ('Whatever the mind of man can conceive and believe, it can achieve.', 'Napoleon Hill', 'wisdom', array['belief'], 'modern'),
    ('What lies behind us and what lies before us are tiny matters compared to what lies within us.', 'Ralph Waldo Emerson', 'wisdom', array['within'], 'classical'),
    ('Beware the barrenness of a busy life.', 'Socrates', 'wisdom', array['busy'], 'ancient'),
    ('A man is but the product of his thoughts. What he thinks, he becomes.', 'Mahatma Gandhi', 'wisdom', array['mind'], 'modern'),
    ('Yesterday I was clever, so I wanted to change the world. Today I am wise, so I am changing myself.', 'Rumi', 'wisdom', array['self','change'], 'ancient'),
    ('First, say to yourself what you would be; and then do what you have to do.', 'Epictetus', 'wisdom', array['stoic','identity'], 'ancient'),

    -- ── LEADERSHIP (decision, others, vision) ────────────────
    ('A leader is one who knows the way, goes the way, and shows the way.', 'John C. Maxwell', 'leadership', array['example'], 'modern'),
    ('The greatest leader is not necessarily the one who does the greatest things. He is the one that gets the people to do the greatest things.', 'Ronald Reagan', 'leadership', array['team'], 'modern'),
    ('Leadership is the capacity to translate vision into reality.', 'Warren Bennis', 'leadership', array['vision'], 'modern'),
    ('Management is doing things right; leadership is doing the right things.', 'Peter Drucker', 'leadership', array['priorities'], 'modern'),
    ('The best way to find out if you can trust somebody is to trust them.', 'Ernest Hemingway', 'leadership', array['trust'], 'modern'),
    ('To handle yourself, use your head; to handle others, use your heart.', 'Eleanor Roosevelt', 'leadership', array['empathy'], 'modern'),
    ('A genuine leader is not a searcher for consensus but a molder of consensus.', 'Martin Luther King Jr.', 'leadership', array['conviction'], 'modern'),
    ('You cannot teach a man anything; you can only help him find it within himself.', 'Galileo Galilei', 'leadership', array['teaching'], 'classical'),
    ('Effective leaders are made, not born. They learn from trial and error.', 'Vince Lombardi', 'leadership', array['practice'], 'modern'),
    ('The function of leadership is to produce more leaders, not more followers.', 'Ralph Nader', 'leadership', array['team'], 'modern'),

    -- ── CREATIVITY (making things, originality) ──────────────
    ('Simplicity is the ultimate sophistication.', 'Leonardo da Vinci', 'creativity', array['simplicity'], 'classical'),
    ('Creativity is intelligence having fun.', 'Albert Einstein', 'creativity', array['play'], 'classical'),
    ('Every artist was first an amateur.', 'Ralph Waldo Emerson', 'creativity', array['beginner'], 'classical'),
    ('Have no fear of perfection — you''ll never reach it.', 'Salvador Dalí', 'creativity', array['perfection'], 'modern'),
    ('Inspiration exists, but it has to find you working.', 'Pablo Picasso', 'creativity', array['work'], 'modern'),
    ('You can''t use up creativity. The more you use, the more you have.', 'Maya Angelou', 'creativity', array['practice'], 'modern'),
    ('Make it work, make it right, make it fast.', 'Kent Beck', 'creativity', array['craft','iterate'], 'modern'),
    ('Constraints are the father of invention.', 'Pablo Picasso', 'creativity', array['constraints'], 'modern'),
    ('Originality is nothing but judicious imitation.', 'Voltaire', 'creativity', array['imitation'], 'classical'),
    ('Imagination is more important than knowledge.', 'Albert Einstein', 'creativity', array['imagination'], 'classical'),
    ('Don''t think. Thinking is the enemy of creativity.', 'Ray Bradbury', 'creativity', array['flow'], 'modern'),

    -- ── FOCUS (attention, deep work, priorities) ─────────────
    ('Focus is a matter of deciding what things you''re not going to do.', 'John Carmack', 'focus', array['priorities'], 'modern'),
    ('Concentrate all your thoughts upon the work at hand. The sun''s rays do not burn until brought to a focus.', 'Alexander Graham Bell', 'focus', array['concentration'], 'classical'),
    ('It is not enough to be busy; so are the ants. The question is: what are we busy about?', 'Henry David Thoreau', 'focus', array['busy'], 'classical'),
    ('Things which matter most must never be at the mercy of things which matter least.', 'Johann Wolfgang von Goethe', 'focus', array['priorities'], 'classical'),
    ('The successful warrior is the average man, with laser-like focus.', 'Bruce Lee', 'focus', array['focus'], 'modern'),
    ('If you spend too much time thinking about a thing, you''ll never get it done.', 'Bruce Lee', 'focus', array['action'], 'modern'),
    ('What gets measured gets managed.', 'Peter Drucker', 'focus', array['measurement'], 'modern'),
    ('You can do anything, but not everything.', 'David Allen', 'focus', array['priorities'], 'modern'),
    ('Lack of direction, not lack of time, is the problem. We all have twenty-four hour days.', 'Zig Ziglar', 'focus', array['direction'], 'modern'),
    ('The shorter way to do many things is to do only one thing at a time.', 'Mozart', 'focus', array['single-task'], 'classical'),
    ('Productivity is never an accident. It is always the result of a commitment to excellence, intelligent planning, and focused effort.', 'Paul J. Meyer', 'focus', array['planning'], 'modern'),

    -- ── COURAGE (fear, risk, conviction) ─────────────────────
    ('He who is not courageous enough to take risks will accomplish nothing in life.', 'Muhammad Ali', 'courage', array['risk'], 'modern'),
    ('You gain strength, courage, and confidence by every experience in which you really stop to look fear in the face.', 'Eleanor Roosevelt', 'courage', array['fear'], 'modern'),
    ('Do one thing every day that scares you.', 'Eleanor Roosevelt', 'courage', array['fear'], 'modern'),
    ('Courage is not the absence of fear, but the triumph over it.', 'Nelson Mandela', 'courage', array['fear'], 'modern'),
    ('To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.', 'Ralph Waldo Emerson', 'courage', array['identity'], 'classical'),
    ('Whether you think you can or you think you can''t, you''re right.', 'Henry Ford', 'courage', array['belief'], 'modern'),
    ('The cave you fear to enter holds the treasure you seek.', 'Joseph Campbell', 'courage', array['fear'], 'modern'),
    ('Twenty years from now you will be more disappointed by the things you didn''t do than by the ones you did.', 'Mark Twain', 'courage', array['regret'], 'modern'),
    ('Boldness has genius, power, and magic in it.', 'Johann Wolfgang von Goethe', 'courage', array['boldness'], 'classical'),
    ('Fortune favors the bold.', 'Virgil', 'courage', array['boldness'], 'ancient'),

    -- ── GROWTH (learning, mindset, improvement) ──────────────
    ('The expert in anything was once a beginner.', 'Helen Hayes', 'growth', array['beginner'], 'modern'),
    ('Live as if you were to die tomorrow. Learn as if you were to live forever.', 'Mahatma Gandhi', 'growth', array['learning'], 'modern'),
    ('If you want to improve, be content to be thought foolish and stupid.', 'Epictetus', 'growth', array['stoic','ego'], 'ancient'),
    ('Anyone who has never made a mistake has never tried anything new.', 'Albert Einstein', 'growth', array['mistakes'], 'classical'),
    ('The only person you should try to be better than is the person you were yesterday.', 'Anonymous', 'growth', array['compare'], 'modern'),
    ('Comfort is the enemy of progress.', 'P. T. Barnum', 'growth', array['discomfort'], 'classical'),
    ('Strength does not come from physical capacity. It comes from an indomitable will.', 'Mahatma Gandhi', 'growth', array['will'], 'modern'),
    ('We cannot solve our problems with the same thinking we used when we created them.', 'Albert Einstein', 'growth', array['thinking'], 'classical'),
    ('Growth is never by mere chance; it is the result of forces working together.', 'James Cash Penney', 'growth', array['systems'], 'modern'),
    ('Tell me and I forget. Teach me and I remember. Involve me and I learn.', 'Benjamin Franklin', 'growth', array['learning'], 'classical'),
    ('Education is what remains after one has forgotten what one has learned in school.', 'Albert Einstein', 'growth', array['learning'], 'classical'),

    -- ── TIME (urgency, the now, mortality) ───────────────────
    ('Lost time is never found again.', 'Benjamin Franklin', 'time', array['urgency'], 'classical'),
    ('Yesterday is gone. Tomorrow has not yet come. We have only today. Let us begin.', 'Mother Teresa', 'time', array['now'], 'modern'),
    ('The two most powerful warriors are patience and time.', 'Leo Tolstoy', 'time', array['patience'], 'classical'),
    ('You may delay, but time will not.', 'Benjamin Franklin', 'time', array['urgency'], 'classical'),
    ('Time is what we want most, but what we use worst.', 'William Penn', 'time', array['urgency'], 'classical'),
    ('Better three hours too soon than a minute too late.', 'William Shakespeare', 'time', array['punctuality'], 'classical'),
    ('Time you enjoy wasting is not wasted time.', 'Marthe Troly-Curtin', 'time', array['rest'], 'modern'),
    ('The bad news is time flies. The good news is you''re the pilot.', 'Michael Altshuler', 'time', array['ownership'], 'modern'),
    ('Until we have begun to go without them, we fail to realize how unnecessary many things are.', 'Seneca', 'time', array['stoic','enough'], 'ancient'),
    ('It''s not that we have a short time to live, but that we waste a lot of it.', 'Seneca', 'time', array['stoic'], 'ancient'),
    ('Realize deeply that the present moment is all you ever have.', 'Eckhart Tolle', 'time', array['present'], 'modern'),
    ('Time is the most valuable thing a man can spend.', 'Theophrastus', 'time', array['value'], 'ancient');
  end if;
end $$;
