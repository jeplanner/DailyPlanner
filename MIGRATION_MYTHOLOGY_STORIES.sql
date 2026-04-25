-- ============================================================
--  DailyPlanner — MYTHOLOGY STORIES (Ramayana + Mahabharata)
--
--  Seeds a curated corpus of well-known episodes from both epics so
--  /mythology can serve a date-stable selection of 5 stories per day.
--  Same day → same 5; new day → new 5. Mix across both epics so each
--  day has variety.
--
--  Schema:
--    mythology_stories(id, epic, title, characters, summary, moral,
--                      source_ref, is_active, created_at)
--
--  Seed: ~40 stories (split roughly 20 / 20). Add more by INSERT —
--  the page will pick them up automatically.
--
--  Safe to re-run.
-- ============================================================

create table if not exists mythology_stories (
  id          uuid primary key default gen_random_uuid(),
  epic        text not null,             -- 'ramayana' | 'mahabharata'
  title       text not null,
  characters  text,                      -- comma-separated names for chip display
  summary     text not null,
  moral       text,
  source_ref  text,                      -- e.g. "Bala Kanda, Sarga 18"
  is_active   boolean default true,
  created_at  timestamptz default now()
);

create index if not exists mythology_stories_active_idx
  on mythology_stories (is_active, epic) where is_active = true;


do $$
begin
  if (select count(*) from mythology_stories) = 0 then
    insert into mythology_stories (epic, title, characters, summary, moral, source_ref) values

    -- ── RAMAYANA ──────────────────────────────────────────────
    ('ramayana', 'The Putrakameshti Yagna',
     'Dasharatha, Rishyasringa, Kausalya, Kaikeyi, Sumitra',
     'King Dasharatha of Ayodhya was childless and grieved deeply. On the advice of his ministers and Sage Vasishtha, he invited Sage Rishyasringa to perform the Putrakameshti yagna. From the sacred fire emerged a celestial being holding a vessel of payasam, the offering of the gods. Dasharatha shared the payasam with his three queens. In time, Kausalya bore Rama, Kaikeyi bore Bharata, and Sumitra bore the twins Lakshmana and Shatrughna — the four princes of Ayodhya.',
     'Patience and right action attract divine grace; what is meant for you arrives in its own time.',
     'Bala Kanda'),

    ('ramayana', 'Vishwamitra Takes the Princes',
     'Vishwamitra, Rama, Lakshmana, Tataka',
     'Sage Vishwamitra arrived at Dasharatha''s court asking that young Rama and Lakshmana accompany him to protect his yagna from rakshasas. Reluctantly Dasharatha agreed. On the journey, the demoness Tataka attacked them — Rama, hesitant to strike a woman, was urged by Vishwamitra to do his duty. He felled her with a single arrow. Vishwamitra then taught the princes celestial weapons (astras) that would later prove decisive against Ravana''s host.',
     'Duty (dharma) sometimes requires acts that feel hard; the wise teacher prepares the student before the trial.',
     'Bala Kanda'),

    ('ramayana', 'Ahalya''s Redemption',
     'Ahalya, Gautama, Rama',
     'On their journey with Vishwamitra, Rama and Lakshmana reached the hermitage where Ahalya stood frozen as stone — cursed by her husband Sage Gautama for an act of betrayal long ago. The curse held that she would be released only by the touch of Rama''s feet. As Rama approached, the dust of his feet fell on her, and Ahalya was restored to life and welcomed home by the forgiving Gautama.',
     'Even long penance finds release in grace; forgiveness restores what shame cannot.',
     'Bala Kanda'),

    ('ramayana', 'Breaking of Shiva''s Bow',
     'Rama, Sita, Janaka, Ravana',
     'King Janaka of Mithila had vowed his daughter Sita would marry only the man who could string the great bow of Shiva. Mighty kings, including Ravana, had failed even to lift it. When Rama arrived in Mithila with Vishwamitra, he lifted the bow, bent it to string, and snapped it in two with a thunder that echoed across the land. Janaka joyfully gave Sita to Rama.',
     'Strength alone is not enough; humility and right intent are what allow it to be wielded.',
     'Bala Kanda'),

    ('ramayana', 'Kaikeyi''s Two Boons',
     'Kaikeyi, Manthara, Dasharatha, Rama, Bharata',
     'On the eve of Rama''s coronation as king, Kaikeyi''s maid Manthara filled her with poisonous fears. Kaikeyi went to Dasharatha and demanded the two boons he had once promised her: that Bharata be crowned, and that Rama be banished to the forest for fourteen years. Bound by his word, the heart-broken king consented. Rama, hearing the news, accepted his exile without a moment''s reproach.',
     'A word given is a debt owed. Composure under injustice is itself a kind of victory.',
     'Ayodhya Kanda'),

    ('ramayana', 'Bharata''s Devotion',
     'Bharata, Rama, the Padukas',
     'Bharata, returning home, learned with horror what his mother had wrought. He refused the throne and travelled to Chitrakoot to plead with Rama to return. Rama gently insisted on keeping his father''s word. Bharata then asked for Rama''s sandals (padukas), placed them upon the throne of Ayodhya, and ruled for fourteen years as their humble servant — a regent, never a king.',
     'True power serves; the willingness to step aside for what is right is itself royal.',
     'Ayodhya Kanda'),

    ('ramayana', 'Surpanakha''s Humiliation',
     'Surpanakha, Rama, Lakshmana, Sita',
     'In the Dandaka forest, the rakshasi Surpanakha — sister of Ravana — saw Rama and was struck with desire. He rebuffed her courteously. She then turned to Lakshmana, who also refused. Enraged, she lunged at Sita; Lakshmana cut off her nose and ears in defense. Wailing, she fled to her brother Khara, then to Ravana — and so the seed of the great war was planted.',
     'Lust unchecked breeds destruction; a small act of impropriety can spiral into catastrophe.',
     'Aranya Kanda'),

    ('ramayana', 'The Golden Deer',
     'Maricha, Rama, Sita, Lakshmana',
     'Lured by Ravana, the rakshasa Maricha took the form of a dazzling golden deer that wandered near Rama''s ashram. Sita begged Rama to bring it for her. As Rama pursued, Maricha mimicked Rama''s voice in distress to draw Lakshmana away too. Sita, alone and frightened, urged Lakshmana to go — and so the protective Lakshmana rekha was drawn, but soon crossed.',
     'Desire blinds judgement; what looks like a gift may be a snare.',
     'Aranya Kanda'),

    ('ramayana', 'Jatayu''s Sacrifice',
     'Jatayu, Sita, Ravana',
     'As Ravana flew off with the abducted Sita, the aged eagle-king Jatayu — old friend of Dasharatha — rose to challenge him. Though far weaker, he fought ferociously, breaking Ravana''s chariot and tearing his bowstring. At last Ravana cut Jatayu''s wings and the great bird fell. He held on to life until Rama arrived, gave the news of Sita''s direction, and died in Rama''s arms — granted moksha.',
     'Honor a duty even at the cost of life; small light against great darkness still matters.',
     'Aranya Kanda'),

    ('ramayana', 'Hanuman Crosses the Ocean',
     'Hanuman, Sampati, Surasa, Sita',
     'Standing on the southern shore, the Vanara army despaired at the hundred-yojana sea. Hanuman alone remembered the boundless strength he had been made to forget by an old curse. Jambavan reminded him; Hanuman grew vast, leapt across the ocean, evaded Surasa the sea-serpent, slew the shadow-catcher Simhika, and reached Lanka — where in the Ashoka grove he at last found Sita beneath a sirisha tree.',
     'You may already be capable of what you fear; the right reminder is sometimes all that''s missing.',
     'Sundara Kanda'),

    ('ramayana', 'The Burning of Lanka',
     'Hanuman, Indrajit, Ravana, Lankans',
     'Captured by Indrajit''s Brahmastra, Hanuman was brought before Ravana, who ordered his tail set ablaze as humiliation. Hanuman extended his tail to enormous length; the Lankans wrapped it in cloth and oil and lit it. Once free, he leapt from rooftop to rooftop, setting fire to every palace except Vibhishana''s and the place Sita was held. Lanka burned. He bowed once more to Sita and returned across the ocean.',
     'A captor''s cruelty can become the captive''s weapon; humility paired with strength is unstoppable.',
     'Sundara Kanda'),

    ('ramayana', 'Building the Ram Setu',
     'Rama, Nala, Nila, Vanara army',
     'To reach Lanka, the Vanara army needed a bridge across the ocean. Rama meditated upon the ocean god Varuna; impatient with no reply, he readied a celestial weapon. Varuna appeared and revealed that Nala, son of Vishwakarma, could build a floating bridge — every stone he set would float. For five days the Vanaras hauled boulders inscribed with Rama''s name; the bridge held; the army crossed.',
     'Persistence at a closed door eventually opens it. Even small hands inscribe stones that hold up nations.',
     'Yuddha Kanda'),

    ('ramayana', 'Sanjeevani Mountain',
     'Hanuman, Lakshmana, Sushena',
     'In the heat of battle, Indrajit struck Lakshmana down with the Shaktibaan. The Vanara physician Sushena said only the four sanjeevani herbs from Mount Dronagiri in the Himalayas could revive him — and only before sunrise. Hanuman flew north, but unable to identify the herbs, he uprooted the entire mountain and brought it to Lanka. Lakshmana was healed; the war turned.',
     'When you can''t make the perfect choice in time, do the whole-hearted one.',
     'Yuddha Kanda'),

    ('ramayana', 'Death of Ravana',
     'Rama, Ravana, Vibhishana',
     'On the final day, Vibhishana counselled Rama: Ravana''s life was hidden in a vessel of nectar in his navel. Rama drew the Brahmastra given by Agastya, charged with the power of all gods, and loosed it. The arrow pierced Ravana''s chest, dried the nectar, and laid him low. Even at the end, the dying Ravana — for all his pride — had been a great scholar of the Vedas; Rama bid Lakshmana go and learn from him.',
     'Honor your enemy''s greatness; victory does not erase the wisdom they once carried.',
     'Yuddha Kanda'),

    ('ramayana', 'Coronation in Ayodhya',
     'Rama, Sita, Bharata, Lakshmana, Hanuman',
     'After fourteen years, Rama returned to Ayodhya in the Pushpaka Vimana. Bharata wept and laid the padukas back at his feet. The city lit lamps along every street to welcome him — the night of Diwali. Rama was crowned king, and his rule (Ram Rajya) became the proverbial age of justice and plenty in which the rains came on time, no child died before its parents, and no harm came to the innocent.',
     'Long exile prepares the heart for true sovereignty; the best ruler is one who has known the forest.',
     'Yuddha Kanda'),

    ('ramayana', 'Hanuman''s Heart',
     'Hanuman, Rama, Sita',
     'Among the gifts presented to Hanuman after the war was a pearl necklace from Sita. He examined each pearl and discarded them all. Asked why, he said he saw no Rama in them. Mocked, he tore open his chest — and there, etched on his heart, were Rama and Sita. Rama embraced him and granted Hanuman that he would live as long as the name of Rama was sung anywhere on earth.',
     'Devotion is not in what is shown but in what is carried within.',
     'Uttara Kanda'),


    -- ── MAHABHARATA ───────────────────────────────────────────
    ('mahabharata', 'Bhishma''s Vow',
     'Devavrata (Bhishma), Shantanu, Satyavati',
     'King Shantanu fell in love with Satyavati, daughter of a fisherman, but her father refused unless her sons would inherit the throne. Devavrata, Shantanu''s heir, took the terrible vow to renounce the throne and remain a lifelong celibate so his father could marry. The gods rained flowers; he was renamed Bhishma — "of the dreadful vow" — and granted the boon of choosing his own time of death.',
     'Some sacrifices echo for generations; great love can be paid in great renunciation.',
     'Adi Parva'),

    ('mahabharata', 'Karna''s Birth',
     'Kunti, Surya, Karna',
     'Young Kunti was given a mantra by Sage Durvasa to summon any god. Curious, she invoked Surya, the sun. To her terror she conceived. The god promised her honour intact and that the child would be born with armour and earrings (kavach-kundal). Unable to keep him as an unwed mother, she set him afloat on a river in a basket. He was found by the charioteer Adhiratha and his wife Radha, who raised him as Karna.',
     'A child''s worth is not in his birth but in what he chooses to become.',
     'Adi Parva'),

    ('mahabharata', 'Ekalavya''s Thumb',
     'Ekalavya, Drona, Arjuna',
     'Drona refused to teach the tribal boy Ekalavya, who quietly built a clay statue of Drona in the forest and trained before it. He surpassed even Arjuna in archery. Drona, finding him, asked for guru-dakshina: Ekalavya''s right thumb. Without hesitation, Ekalavya cut it off and offered it. He continued to shoot, but never with the same skill — preserving Arjuna''s preeminence.',
     'Devotion can compass what a teacher refuses to give. Loyalty has a cost the loyal are willing to pay.',
     'Adi Parva'),

    ('mahabharata', 'House of Lac',
     'Duryodhana, Pandavas, Kunti, Vidura',
     'Jealous of the Pandavas, Duryodhana built a palace in Varanavata of lac and combustibles, planning to burn them alive. Forewarned by the wise Vidura through a coded message, the Pandavas dug a tunnel beneath the palace. On the chosen night, when Purochana set the fire, the Pandavas escaped through the tunnel and let the world believe them dead.',
     'Trust those who speak in riddles when the open word is dangerous; survival sometimes asks for invisibility.',
     'Adi Parva'),

    ('mahabharata', 'Bhima Slays Hidimba',
     'Bhima, Hidimba, Hidimbi, Ghatotkacha',
     'In the forest, the rakshasa Hidimba sent his sister Hidimbi to lure the sleeping Pandavas. Instead, Hidimbi fell in love with Bhima and warned them. When Hidimba attacked, Bhima slew him in a great fight. Hidimbi married Bhima with Kunti''s blessing; their son was Ghatotkacha, the giant who would one day take a divine spear meant for Arjuna.',
     'Even a foe can become an ally; the heart finds its own path through hostile country.',
     'Adi Parva'),

    ('mahabharata', 'Draupadi''s Swayamvar',
     'Draupadi, Drupada, Arjuna, Karna',
     'King Drupada announced his daughter Draupadi''s swayamvar: a fish hung from a high pole, to be shot through its eye while looking only at its reflection in the water below. Karna lifted the bow, but Draupadi, knowing his birth as a sutaputra, declined. A young brahmin — Arjuna in disguise — strung the bow and pierced the eye. Draupadi was won; the Pandavas revealed themselves.',
     'Skill that has not asked for the prize has the steadiest hand.',
     'Adi Parva'),

    ('mahabharata', 'The Game of Dice',
     'Yudhishthira, Shakuni, Duryodhana, Draupadi',
     'Shakuni lured Yudhishthira into a game of dice with loaded ivory. The eldest Pandava, bound by kshatriya code not to refuse a challenge, lost his wealth, kingdom, brothers, himself — and finally his queen Draupadi. She was dragged into court, where Dushasana attempted to disrobe her. Krishna''s grace lengthened her sari into endless cloth; her vow that her hair would remain unbraided until washed in Dushasana''s blood would echo to Kurukshetra.',
     'A single weakness in the wise can undo what a lifetime of right action built.',
     'Sabha Parva'),

    ('mahabharata', 'The Yaksha Prashna',
     'Yudhishthira, the Yaksha (Yama)',
     'In the forest, the four younger Pandavas drank from a lake and fell dead — a Yaksha had warned them not to drink before answering his questions. Yudhishthira arrived, answered each riddle with quiet wisdom, and the Yaksha — Yama in disguise — offered to revive one brother. Yudhishthira chose Nakula. Asked why, he said: his mother Kunti deserved that one of her sons live, and Nakula was Madri''s. The Yaksha, moved, revived all four.',
     'Justice is what we owe even those who are not standing in front of us.',
     'Vana Parva'),

    ('mahabharata', 'Krishna''s Peace Mission',
     'Krishna, Duryodhana, Bhishma, Vidura, Karna',
     'Before war, Krishna went to Hastinapura asking only five villages for the Pandavas — peace at any price. Duryodhana refused even a needlepoint of land. Furious, Krishna revealed his cosmic form (vishwarupa) in the assembly. The elders bowed; Duryodhana stood unmoved. War became inevitable.',
     'Peace requires that one side will accept less than they could; pride that refuses small concessions invites the largest losses.',
     'Udyoga Parva'),

    ('mahabharata', 'The Bhagavad Gita',
     'Krishna, Arjuna',
     'On the field of Kurukshetra, seeing his own grandfather, teacher, and cousins arrayed against him, Arjuna let his bow slip from his hand and refused to fight. Krishna, his charioteer, then taught him the Gita — on duty, the eternal soul, the three paths of karma, jnana, and bhakti, and finally revealed his vishwarupa. Arjuna lifted his bow.',
     'Action without attachment to fruit is the path of the steady mind. Duty rightly understood ends paralysis.',
     'Bhishma Parva'),

    ('mahabharata', 'Bhishma''s Bed of Arrows',
     'Bhishma, Arjuna, Shikhandi',
     'For ten days Bhishma was unconquerable. Knowing he would not strike one born female, the Pandavas placed Shikhandi — born Shikhandini — before Arjuna''s bow. From behind Shikhandi, Arjuna''s arrows pierced Bhishma so densely that when he fell he did not touch the ground; he lay on a bed of his own grandson''s arrows. He waited fifty-eight days for Uttarayana to claim his chosen death.',
     'Even invincibility has a precise condition; the wise commander finds the seam.',
     'Bhishma Parva'),

    ('mahabharata', 'Abhimanyu in the Chakravyuha',
     'Abhimanyu, Drona, Jayadratha, Arjuna',
     'On the thirteenth day, the Kauravas formed the chakravyuha — a deadly seven-tier spiral. Only Arjuna and Krishna knew its full secret; Abhimanyu, learning it as an unborn child, knew how to enter but not how to leave. He broke through six tiers alone, killed mighty warriors, and at the centre was surrounded by seven maharathis at once and slain. Arjuna vowed to kill Jayadratha — who had blocked the rear — by the next sunset, or burn himself alive.',
     'Half a plan is enough to begin but not enough to return; teach the whole way out.',
     'Drona Parva'),

    ('mahabharata', 'Karna and the Wheel',
     'Karna, Arjuna, Krishna',
     'On the seventeenth day, Karna and Arjuna at last faced each other. The earth itself swallowed Karna''s chariot wheel — the curse of a brahmin he had wronged unknowingly returning. As Karna stepped down to lift it, he asked Arjuna for a moment''s pause, citing dharma. Krishna reminded Arjuna of every dharma the Kauravas had broken — Draupadi, Abhimanyu — and bade him shoot. Karna fell.',
     'The hour for mercy is before the betrayal, not after. Past wrongs are not erased by an opportune appeal.',
     'Karna Parva'),

    ('mahabharata', 'Bhima Slays Duryodhana',
     'Bhima, Duryodhana, Krishna, Balarama',
     'After all his brothers fell, Duryodhana hid in a lake. Drawn out by taunts, he fought Bhima with a mace. By rule, the strike below the waist was forbidden. Krishna reminded Bhima of his vow to break the thigh on which Draupadi had been seated. Bhima struck. Duryodhana fell, and so the war ended — though Balarama, Krishna''s brother, was so angered by the unfair stroke that Krishna had to talk him down.',
     'Vows demand precision; rules demand judgement. The two sometimes collide.',
     'Shalya Parva'),

    ('mahabharata', 'Ashwatthama''s Curse',
     'Ashwatthama, Krishna, Pandavas',
     'After the war, Ashwatthama crept into the Pandava camp at night and slaughtered Draupadi''s sleeping sons, mistaking them for the brothers. Captured, he was stripped of the gem on his forehead by Bhima but spared by Krishna, who cursed him to wander the earth bleeding and unable to die for three thousand years.',
     'Vengeance taken on innocents stains beyond death; some prisons are worse than the noose.',
     'Sauptika Parva'),

    ('mahabharata', 'Yudhishthira and the Dog',
     'Yudhishthira, the dog (Yama), Indra',
     'The Pandavas, with a dog that had followed them, climbed Himavan toward heaven. One by one — Draupadi, the brothers — they fell. Only Yudhishthira and the dog reached the gates. Indra invited Yudhishthira aboard his chariot, but said the dog could not enter. Yudhishthira refused: a creature that had walked beside him faithfully could not be abandoned for a kingdom of gods. The dog revealed himself as Yama, his father; the gates opened.',
     'Loyalty owed to the smallest companion is the door to the highest.',
     'Mahaprasthanika Parva'),

    ('mahabharata', 'Krishna and the Hunter',
     'Krishna, Jara',
     'After the great war, Krishna sat alone beneath a peepal tree, his foot raised. A hunter named Jara, mistaking the sole of Krishna''s foot for a deer''s ear, loosed his arrow. Realising what he had done, the hunter wept; Krishna comforted him — this was the consequence of an old curse from the Ramayana''s Vali, born again as Jara — and so Krishna left the body and the world.',
     'Even avatars complete the karma they entered; nothing is dropped, only carried through.',
     'Mausala Parva');

  end if;
end $$;
